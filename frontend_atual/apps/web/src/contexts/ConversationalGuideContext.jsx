
import React, { createContext, useContext, useState } from 'react';
import {
  createGuideDestination,
  normalizeFamilyMemberCount,
  normalizeGuideDestinations,
  serializeGuideDestinations,
} from '@/utils/guide-form.js';

const ConversationalGuideContext = createContext();

export const useConversationalGuide = () => {
  const context = useContext(ConversationalGuideContext);
  if (!context) {
    throw new Error('useConversationalGuide must be used within a ConversationalGuideProvider');
  }
  return context;
};

export const ConversationalGuideProvider = ({ children }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [familyName, setFamilyName] = useState('');
  const [coverPhoto, setCoverPhoto] = useState(null);
  const [coverPhotoUrl, setCoverPhotoUrl] = useState('');
  const [expectedCoverFamilyMemberCount, setExpectedCoverFamilyMemberCount] = useState(0);
  const [destination, setDestination] = useState('');
  const [destinationsList, setDestinationsListState] = useState([createGuideDestination()]);
  const [itineraryMode, setItineraryMode] = useState('known');

  // Family Details State
  const [childrenList, setChildrenList] = useState([]);
  const [parentsList, setParentsList] = useState([]);
  const [year, setYear] = useState(2026);

  // Minerva API Integration State
  const [parsedData, setParsedData] = useState({ destinations: [], landmarks: [] });
  const [selectedLandmarks, setSelectedLandmarks] = useState([]); // Array of IDs
  const [recommendedItinerary, setRecommendedItinerary] = useState(null);
  const [restaurantRecommendationsExtra, setRestaurantRecommendationsExtra] = useState(false);
  const [itineraryPreferences, setItineraryPreferences] = useState({
    days: 3,
    interests: [],
    pace: 'balanced',
  });
  const [isLoadingLandmarks, setIsLoadingLandmarks] = useState(false);
  const [hasSearchedLandmarks, setHasSearchedLandmarks] = useState(false);

  const setStep = (step) => {
    setCurrentStep(step);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const nextStep = () => {
    setStep(Math.min(currentStep + 1, 6));
  };

  const goBack = () => {
    setStep(Math.max(currentStep - 1, 1));
  };

  const updateFamilyName = (name) => setFamilyName(name);

  const updateCoverPhoto = (file) => {
    setCoverPhoto(file);
    if (file) {
      setCoverPhotoUrl(URL.createObjectURL(file));
    } else {
      setCoverPhotoUrl('');
    }
  };

  const updateExpectedCoverFamilyMemberCount = (count) => {
    setExpectedCoverFamilyMemberCount(normalizeFamilyMemberCount(count));
  };

  const resetRouteData = (nextDestination = '') => {
    setDestination(nextDestination);
    setHasSearchedLandmarks(false);
    setParsedData({ destinations: [], landmarks: [] });
    setSelectedLandmarks([]);
    setRecommendedItinerary(null);
  };

  const updateDestination = (dest) => {
    resetRouteData(dest);
  };

  const updateDestinationsList = (destinations) => {
    const normalized = normalizeGuideDestinations(destinations);
    const summary = serializeGuideDestinations(normalized);
    setDestinationsListState(normalized);
    if (summary !== destination) {
      resetRouteData(summary);
    } else {
      setDestination(summary);
    }
  };

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
        recommendedItinerary,
        setRecommendedItinerary,
        restaurantRecommendationsExtra,
        setRestaurantRecommendationsExtra,
        itineraryPreferences,
        setItineraryPreferences,
        isLoadingLandmarks,
        setIsLoadingLandmarks,
        hasSearchedLandmarks,
        setHasSearchedLandmarks
      }}
    >
      {children}
    </ConversationalGuideContext.Provider>
  );
};
