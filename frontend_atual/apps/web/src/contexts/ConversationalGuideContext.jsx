
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  createGuideDestination,
  normalizeFamilyMemberCount,
  normalizeGuideDestinations,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';
import {
  createGuideDraft,
  discardGuideDraft,
  getCurrentGuideDraft,
  updateGuideDraft,
} from '@/utils/minerva-api.js';
import {
  normalizeLandmarkActivitySelections,
  pruneLandmarkActivitySelections,
} from '@/utils/landmark-activities.js';
import { useAuth } from '@/contexts/AuthContext.jsx';
import {
  builderSessionIdFromLocation,
  clearGuideProgressSnapshot,
  normalizeBuilderSessionId,
  readGuideProgressSnapshot,
  replaceBuilderSessionInLocation,
  selectNewestGuideProgress,
  writeGuideProgressSnapshot,
} from '@/utils/guide-progress.js';

const ConversationalGuideContext = createContext();

const GUIDE_DRAFT_SCHEMA_VERSION = 2;

const hasMeaningfulDraftContent = (payload) => Boolean(
  payload.builder_session_id ||
  payload.family_name ||
  payload.destination ||
  payload.children_list?.length ||
  payload.parents_list?.length ||
  payload.selected_landmarks?.length ||
  payload.destinations_list?.some((item) => (
    item.place || item.timing || item.landmarks?.some(Boolean)
  ))
);

export const useConversationalGuide = () => {
  const context = useContext(ConversationalGuideContext);
  if (!context) {
    throw new Error('useConversationalGuide must be used within a ConversationalGuideProvider');
  }
  return context;
};

export const ConversationalGuideProvider = ({ children }) => {
  const { user, isAuthenticated, isLoading: isAuthLoading } = useAuth();
  const ownerId = String(user?.id || '').trim();
  const [currentStep, setCurrentStep] = useState(1);
  const [familyName, setFamilyName] = useState('');
  const [coverPhoto, setCoverPhoto] = useState(null);
  const [coverPhotoUrl, setCoverPhotoUrl] = useState('');
  const [expectedCoverFamilyMemberCount, setExpectedCoverFamilyMemberCount] = useState(0);
  const [photoProcessingConsent, setPhotoProcessingConsent] = useState(false);
  const [privacyConsentAt, setPrivacyConsentAt] = useState('');
  const [destination, setDestination] = useState('');
  const [destinationsList, setDestinationsListState] = useState(
    () => [createGuideDestination()]
  );
  const [itineraryMode, setItineraryMode] = useState('known');

  // Family Details State
  const [childrenList, setChildrenList] = useState([]);
  const [parentsList, setParentsList] = useState([]);
  const [year, setYear] = useState(2026);

  // Minerva API Integration State
  const [parsedData, setParsedData] = useState({ destinations: [], landmarks: [] });
  const [selectedLandmarks, setSelectedLandmarks] = useState([]); // Array of IDs
  const [landmarkActivitySelections, setLandmarkActivitySelections] = useState([]);
  const [recommendedItinerary, setRecommendedItinerary] = useState(null);
  const [restaurantRecommendationsExtra, setRestaurantRecommendationsExtra] = useState(false);
  const [itineraryPreferences, setItineraryPreferences] = useState({
    days: 3,
    interests: [],
    pace: 'balanced',
  });
  const [isLoadingLandmarks, setIsLoadingLandmarks] = useState(false);
  const [hasSearchedLandmarks, setHasSearchedLandmarks] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [restoredDraftId, setRestoredDraftId] = useState(null);
  const [restoredDestinationsList, setRestoredDestinationsList] = useState(null);
  const [draftResetKey, setDraftResetKey] = useState(0);
  const [draftRevision, setDraftRevision] = useState(null);
  const [draftStatus, setDraftStatus] = useState('loading');
  const [draftError, setDraftError] = useState('');
  const [draftReady, setDraftReady] = useState(false);
  const [restoredProgress, setRestoredProgress] = useState(false);
  const [builderSessionId, setBuilderSessionIdState] = useState('');
  const lastSavedDraftPayload = useRef('');
  const saveInFlight = useRef(false);
  const saveQueued = useRef(false);
  const draftReadyRef = useRef(false);
  const draftIdRef = useRef(null);
  const draftRevisionRef = useRef(null);
  const latestGuideDraftPayload = useRef(null);
  const mountedRef = useRef(true);

  const guideDraftPayload = useMemo(() => ({
    schema_version: GUIDE_DRAFT_SCHEMA_VERSION,
    current_step: currentStep,
    builder_session_id: builderSessionId,
    family_name: familyName,
    destination,
    destinations_list: destinationsList,
    itinerary_mode: itineraryMode,
    children_list: childrenList,
    parents_list: parentsList,
    year,
    parsed_data: parsedData,
    selected_landmarks: selectedLandmarks,
    landmark_activity_selections: landmarkActivitySelections,
    recommended_itinerary: recommendedItinerary,
    restaurant_recommendations_extra: restaurantRecommendationsExtra,
    itinerary_preferences: itineraryPreferences,
    has_searched_landmarks: hasSearchedLandmarks,
    expected_cover_family_member_count: expectedCoverFamilyMemberCount,
  }), [
    builderSessionId,
    childrenList,
    currentStep,
    destination,
    destinationsList,
    familyName,
    hasSearchedLandmarks,
    expectedCoverFamilyMemberCount,
    itineraryMode,
    itineraryPreferences,
    landmarkActivitySelections,
    parentsList,
    parsedData,
    recommendedItinerary,
    restaurantRecommendationsExtra,
    selectedLandmarks,
    year,
  ]);

  latestGuideDraftPayload.current = guideDraftPayload;
  draftIdRef.current = draftId;
  draftRevisionRef.current = draftRevision;
  draftReadyRef.current = draftReady;

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const persistLatestDraft = useCallback(async () => {
    if (!draftReadyRef.current) return false;
    if (saveInFlight.current) {
      saveQueued.current = true;
      return true;
    }

    saveInFlight.current = true;
    let succeeded = true;
    try {
      do {
        saveQueued.current = false;
        const payload = latestGuideDraftPayload.current;
        const serialized = JSON.stringify(payload);
        if (!hasMeaningfulDraftContent(payload) || serialized === lastSavedDraftPayload.current) {
          break;
        }
        if (mountedRef.current) {
          setDraftStatus('saving');
          setDraftError('');
        }
        try {
          const saved = draftIdRef.current && draftRevisionRef.current
            ? await updateGuideDraft(
                draftIdRef.current,
                {
                  title: 'Rascunho de guia',
                  payload,
                  revision: draftRevisionRef.current,
                },
              )
            : await createGuideDraft({ title: 'Rascunho de guia', payload });
          lastSavedDraftPayload.current = serialized;
          draftIdRef.current = saved.id;
          draftRevisionRef.current = saved.revision;
          if (mountedRef.current) {
            setDraftId(saved.id);
            setDraftRevision(saved.revision);
            setDraftStatus('saved');
          }
        } catch (error) {
          succeeded = false;
          if (mountedRef.current) {
            setDraftStatus('error');
            setDraftError(error.message || 'Não foi possível salvar o rascunho. Tente novamente.');
          }
          break;
        }
      } while (
        saveQueued.current
        || JSON.stringify(latestGuideDraftPayload.current) !== lastSavedDraftPayload.current
      );
    } finally {
      saveInFlight.current = false;
    }
    return succeeded;
  }, []);

  useEffect(() => {
    if (isAuthLoading || !isAuthenticated || !ownerId) return undefined;
    let active = true;
    setDraftReady(false);
    draftReadyRef.current = false;
    setDraftStatus('loading');
    setDraftError('');

    const restore = async () => {
      const snapshot = readGuideProgressSnapshot(globalThis.localStorage, ownerId);
      let draft = null;
      let serverError = null;
      try {
        draft = await getCurrentGuideDraft();
      } catch (error) {
        serverError = error;
      }
      if (!active) return;

      const selected = selectNewestGuideProgress({ draft, snapshot });
      const urlBuilderSessionId = builderSessionIdFromLocation();
      if (selected?.payload || urlBuilderSessionId) {
        const originalPayload = selected?.payload || {};
        const restoredBuilderSessionId = urlBuilderSessionId
          || normalizeBuilderSessionId(originalPayload.builder_session_id);
        const restoredStep = Math.min(7, Math.max(1, Number(originalPayload.current_step) || 1));
        const payload = {
          ...originalPayload,
          schema_version: GUIDE_DRAFT_SCHEMA_VERSION,
          current_step: restoredBuilderSessionId ? 7 : restoredStep,
          builder_session_id: restoredBuilderSessionId,
        };
        setCurrentStep(payload.current_step);
        setBuilderSessionIdState(restoredBuilderSessionId);
        if (restoredBuilderSessionId) {
          replaceBuilderSessionInLocation(restoredBuilderSessionId);
        }
        setFamilyName(String(payload.family_name || ''));
        setDestination(String(payload.destination || ''));
        const restoredDestinations = Array.isArray(payload.destinations_list)
          && payload.destinations_list.length
          ? normalizeGuideDestinations(payload.destinations_list)
          : [createGuideDestination()];
        setDestinationsListState(restoredDestinations);
        setRestoredDestinationsList(restoredDestinations);
        setItineraryMode(['known', 'freeform', 'suggested'].includes(payload.itinerary_mode)
          ? payload.itinerary_mode
          : 'known');
        setChildrenList(Array.isArray(payload.children_list) ? payload.children_list : []);
        setParentsList(Array.isArray(payload.parents_list) ? payload.parents_list : []);
        setYear(Number(payload.year) || 2026);
        setParsedData(payload.parsed_data && typeof payload.parsed_data === 'object'
          ? payload.parsed_data
          : { destinations: [], landmarks: [] });
        setSelectedLandmarks(
          Array.isArray(payload.selected_landmarks) ? payload.selected_landmarks : [],
        );
        setLandmarkActivitySelections(
          normalizeLandmarkActivitySelections(payload.landmark_activity_selections),
        );
        setRecommendedItinerary(payload.recommended_itinerary || null);
        setRestaurantRecommendationsExtra(Boolean(payload.restaurant_recommendations_extra));
        setItineraryPreferences(
          payload.itinerary_preferences && typeof payload.itinerary_preferences === 'object'
            ? payload.itinerary_preferences
            : { days: 3, interests: [], pace: 'balanced' },
        );
        setHasSearchedLandmarks(Boolean(payload.has_searched_landmarks));
        setExpectedCoverFamilyMemberCount(
          normalizeFamilyMemberCount(payload.expected_cover_family_member_count),
        );
        latestGuideDraftPayload.current = payload;
        setRestoredProgress(true);
      }

      if (draft) {
        draftIdRef.current = draft.id;
        draftRevisionRef.current = draft.revision;
        setDraftId(draft.id);
        setRestoredDraftId(draft.id);
        setDraftRevision(draft.revision);
        lastSavedDraftPayload.current = JSON.stringify(draft.payload || {});
      }

      if (serverError) {
        setDraftStatus(snapshot ? 'local' : 'error');
        setDraftError(snapshot
          ? 'Seu progresso foi recuperado neste dispositivo e será sincronizado quando a conexão voltar.'
          : 'Não foi possível recuperar seu rascunho. Tente recarregar a página.');
      } else {
        setDraftStatus(draft && selected?.source !== 'local' ? 'saved' : 'idle');
      }
      draftReadyRef.current = true;
      setDraftReady(true);
    };

    restore();
    return () => {
      active = false;
    };
  }, [isAuthLoading, isAuthenticated, ownerId]);

  useEffect(() => {
    if (!draftReady || !ownerId) return;
    try {
      writeGuideProgressSnapshot(
        globalThis.localStorage,
        ownerId,
        guideDraftPayload,
        new Date().toISOString(),
        draftRevisionRef.current,
      );
    } catch {
      // Server-side autosave remains authoritative when browser storage is unavailable.
    }
  }, [draftReady, guideDraftPayload, ownerId]);

  useEffect(() => {
    if (!draftReady || !hasMeaningfulDraftContent(guideDraftPayload)) return undefined;
    const serialized = JSON.stringify(guideDraftPayload);
    if (serialized === lastSavedDraftPayload.current) return undefined;
    const timer = window.setTimeout(persistLatestDraft, 800);
    return () => window.clearTimeout(timer);
  }, [draftReady, guideDraftPayload, persistLatestDraft]);

  const checkpointBuilderSession = useCallback(async (sessionId) => {
    const normalized = normalizeBuilderSessionId(sessionId);
    if (!normalized) throw new Error('Identificador da montagem inválido.');
    const payload = {
      ...latestGuideDraftPayload.current,
      schema_version: GUIDE_DRAFT_SCHEMA_VERSION,
      current_step: 7,
      builder_session_id: normalized,
    };
    latestGuideDraftPayload.current = payload;
    setCurrentStep(7);
    setBuilderSessionIdState(normalized);
    replaceBuilderSessionInLocation(normalized);
    try {
      writeGuideProgressSnapshot(
        globalThis.localStorage,
        ownerId,
        payload,
        new Date().toISOString(),
        draftRevisionRef.current,
      );
    } catch {
      // The authenticated draft save below remains available.
    }
    return persistLatestDraft();
  }, [ownerId, persistLatestDraft]);

  const clearBuilderSessionCheckpoint = useCallback(async ({ returnToPhoto = false } = {}) => {
    const payload = {
      ...latestGuideDraftPayload.current,
      schema_version: GUIDE_DRAFT_SCHEMA_VERSION,
      current_step: returnToPhoto ? 6 : currentStep,
      builder_session_id: '',
    };
    latestGuideDraftPayload.current = payload;
    setBuilderSessionIdState('');
    if (returnToPhoto) setCurrentStep(6);
    replaceBuilderSessionInLocation('');
    try {
      writeGuideProgressSnapshot(
        globalThis.localStorage,
        ownerId,
        payload,
        new Date().toISOString(),
        draftRevisionRef.current,
      );
    } catch {
      // The authenticated draft save below remains available.
    }
    return persistLatestDraft();
  }, [currentStep, ownerId, persistLatestDraft]);

  const discardDraft = async () => {
    try {
      if (draftIdRef.current) await discardGuideDraft(draftIdRef.current);
    } catch (error) {
      setDraftStatus('error');
      setDraftError(error.message || 'Não foi possível descartar o rascunho.');
      return false;
    }
    setDraftId(null);
    draftIdRef.current = null;
    setRestoredDraftId(null);
    setRestoredDestinationsList(null);
    setDraftRevision(null);
    draftRevisionRef.current = null;
    setDraftStatus('idle');
    setDraftError('');
    lastSavedDraftPayload.current = '';
    clearGuideProgressSnapshot(globalThis.localStorage, ownerId);
    replaceBuilderSessionInLocation('');
    setBuilderSessionIdState('');
    setRestoredProgress(false);
    setCurrentStep(1);
    setFamilyName('');
    updateCoverPhoto(null);
    setExpectedCoverFamilyMemberCount(0);
    setPhotoProcessingConsent(false);
    setPrivacyConsentAt('');
    setDestination('');
    setDestinationsListState([createGuideDestination()]);
    setItineraryMode('known');
    setChildrenList([]);
    setParentsList([]);
    setYear(2026);
    setParsedData({ destinations: [], landmarks: [] });
    setSelectedLandmarks([]);
    setLandmarkActivitySelections([]);
    setRecommendedItinerary(null);
    setRestaurantRecommendationsExtra(false);
    setItineraryPreferences({ days: 3, interests: [], pace: 'balanced' });
    setHasSearchedLandmarks(false);
    setDraftResetKey((value) => value + 1);
    return true;
  };

  const setStep = (step) => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // No modo "Ja sei o roteiro" a etapa de preferencias (2) e pulada: o usuario
  // ja informou os pontos turisticos e vai direto para a confirmacao com fotos.
  const nextStep = () => {
    const skipPreferences = itineraryMode === 'known' && currentStep === 1;
    setStep(Math.min(skipPreferences ? 3 : currentStep + 1, 7));
  };

  const goBack = () => {
    const skipPreferences = itineraryMode === 'known' && currentStep === 3;
    setStep(Math.max(skipPreferences ? 1 : currentStep - 1, 1));
  };

  const updateFamilyName = (name) => setFamilyName(name);

  const updateCoverPhoto = (file) => {
    setCoverPhoto(file);
    setCoverPhotoUrl((previousUrl) => {
      if (previousUrl) URL.revokeObjectURL(previousUrl);
      return file ? URL.createObjectURL(file) : '';
    });
  };

  const updatePhotoProcessingConsent = (granted) => {
    const accepted = Boolean(granted);
    setPhotoProcessingConsent(accepted);
    setPrivacyConsentAt(accepted ? new Date().toISOString() : '');
  };

  const updateExpectedCoverFamilyMemberCount = (count) => {
    setExpectedCoverFamilyMemberCount(normalizeFamilyMemberCount(count));
  };

  const resetRouteData = useCallback((nextDestination = '') => {
    setDestination(nextDestination);
    setHasSearchedLandmarks(false);
    setParsedData({ destinations: [], landmarks: [] });
    setSelectedLandmarks([]);
    setLandmarkActivitySelections([]);
    setRecommendedItinerary(null);
  }, []);

  const updateDestination = useCallback((dest) => {
    resetRouteData(dest);
  }, [resetRouteData]);

  const updateDestinationsList = useCallback((destinations) => {
    const normalized = normalizeGuideDestinations(destinations);
    const summary = serializeGuideDestinations(normalized);
    setDestinationsListState(normalized);
    resetRouteData(summary);
  }, [resetRouteData]);

  const setParsedDataState = (data) => {
    setParsedData(data);
  };

  const toggleLandmarkSelection = (landmarkId) => {
    setSelectedLandmarks(prev => {
      if (prev.includes(landmarkId)) {
        return prev.filter(id => id !== landmarkId);
      }
      return [...prev, landmarkId];
    });
  };

  useEffect(() => {
    const selectedIds = new Set(selectedLandmarks.map((id) => String(id)));
    const selectedCanonicalIds = (parsedData.landmarks || [])
      .filter((landmark) =>
        selectedIds.has(String(landmark.id)) ||
        selectedIds.has(String(landmark.selection_id)),
      )
      .map((landmark) => landmark.selection_id || landmark.id);
    setLandmarkActivitySelections((current) => {
      const next = pruneLandmarkActivitySelections(
        current,
        selectedCanonicalIds.length > 0 ? selectedCanonicalIds : selectedLandmarks,
      );
      return JSON.stringify(next) === JSON.stringify(current) ? current : next;
    });
  }, [parsedData.landmarks, selectedLandmarks]);

  return (
    <ConversationalGuideContext.Provider
      value={{
        currentStep,
        setStep,
        nextStep,
        goBack,
        familyName,
        updateFamilyName,
        coverPhoto,
        coverPhotoUrl,
        updateCoverPhoto,
        expectedCoverFamilyMemberCount,
        updateExpectedCoverFamilyMemberCount,
        photoProcessingConsent,
        privacyConsentAt,
        updatePhotoProcessingConsent,
        destination,
        updateDestination,
        destinationsList,
        updateDestinationsList,
        itineraryMode,
        setItineraryMode,

        // Family Details
        childrenList,
        setChildrenList,
        parentsList,
        setParentsList,
        year,
        setYear,

        // Landmark state
        parsedData,
        setParsedData: setParsedDataState,
        selectedLandmarks,
        setSelectedLandmarks,
        toggleLandmarkSelection,
        landmarkActivitySelections,
        setLandmarkActivitySelections,
        recommendedItinerary,
        setRecommendedItinerary,
        restaurantRecommendationsExtra,
        setRestaurantRecommendationsExtra,
        itineraryPreferences,
        setItineraryPreferences,
        isLoadingLandmarks,
        setIsLoadingLandmarks,
        hasSearchedLandmarks,
        setHasSearchedLandmarks,

        // Serializable progress is checkpointed per owner in the browser and
        // saved server-side. Photo bytes and consent deliberately stay ephemeral.
        draftId,
        restoredDraftId,
        restoredDestinationsList,
        draftResetKey,
        draftStatus,
        draftError,
        draftReady,
        restoredProgress,
        builderSessionId,
        checkpointBuilderSession,
        clearBuilderSessionCheckpoint,
        discardDraft,
      }}
    >
      {children}
    </ConversationalGuideContext.Provider>
  );
};
