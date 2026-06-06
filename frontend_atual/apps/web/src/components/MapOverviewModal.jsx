import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  Check,
  Clock3,
  ExternalLink,
  Loader2,
  MapPin,
  Plus,
  Route,
  Sparkles,
  X,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  clearGoogleMarkers,
  googleMapsBrowserKey,
  googleMapsMapId,
  loadGoogleMaps,
} from '@/utils/google-maps.js';
import { tripMapExplorerItems } from '@/utils/minerva-api.js';

const createMarkerContent = (landmark, { isSelected, isHighlighted }) => {
  const wrapper = document.createElement('button');
  wrapper.type = 'button';
  wrapper.className = [
    'relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-full border-2 shadow-lg transition-transform',
    isHighlighted
      ? 'border-primary bg-primary ring-4 ring-primary/25'
      : isSelected
        ? 'border-primary bg-primary'
        : 'border-white bg-secondary',
  ].join(' ');
  wrapper.style.transform = isHighlighted ? 'scale(1.18)' : isSelected ? 'scale(1.08)' : 'scale(1)';
  wrapper.style.boxShadow = isHighlighted
    ? '0 18px 40px rgba(15, 23, 42, 0.35)'
    : '0 10px 24px rgba(15, 23, 42, 0.22)';

  if (landmark.image) {
    const image = document.createElement('img');
    image.src = landmark.image;
    image.alt = landmark.name;
    image.className = 'h-full w-full object-cover';
    wrapper.appendChild(image);
  } else {
    const label = document.createElement('span');
    label.className = 'text-sm font-bold text-white';
    label.textContent = landmark.name?.slice(0, 1) || '?';
    wrapper.appendChild(label);
  }

  const status = document.createElement('span');
  status.className = [
    'absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold text-white',
    isSelected ? 'bg-primary' : 'bg-secondary',
  ].join(' ');
  status.textContent = isSelected ? 'OK' : '+';
  wrapper.appendChild(status);

  return wrapper;
};

const filterOptions = [
  { label: 'Todos', value: 'all' },
  { label: 'No roteiro', value: 'selected' },
  { label: 'Sugeridos', value: 'suggested' },
];

const MapOverviewModal = ({
  open,
  landmarks,
  selectedLandmarks,
  onToggleLandmark,
  onExploreMore,
  isExploringMore = false,
  exploreError = '',
  exploreNotice = '',
  onClose,
}) => {
  const apiKey = googleMapsBrowserKey();
  const mapId = googleMapsMapId();
  const mapElementRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef([]);
  const boundsSignatureRef = useRef('');
  const [loadError, setLoadError] = useState('');
  const [activeLandmarkId, setActiveLandmarkId] = useState('');
  const [hoveredLandmarkId, setHoveredLandmarkId] = useState('');
  const [viewFilter, setViewFilter] = useState('all');

  const selectedSet = useMemo(() => new Set(selectedLandmarks), [selectedLandmarks]);
  const mapLandmarks = useMemo(
    () => tripMapExplorerItems(landmarks, selectedLandmarks),
    [landmarks, selectedLandmarks]
  );
  const filteredLandmarks = useMemo(() => {
    if (viewFilter === 'selected') {
      return mapLandmarks.filter((landmark) => landmark.map_status === 'selected');
    }
    if (viewFilter === 'suggested') {
      return mapLandmarks.filter((landmark) => landmark.map_status === 'suggested');
    }
    return mapLandmarks;
  }, [mapLandmarks, viewFilter]);
  const selectedCount = mapLandmarks.filter((landmark) => landmark.map_status === 'selected').length;
  const suggestedCount = mapLandmarks.length - selectedCount;
  const highlightedLandmarkId = hoveredLandmarkId || activeLandmarkId;
  const activeLandmark = (
    mapLandmarks.find((landmark) => landmark.id === highlightedLandmarkId) ||
    mapLandmarks.find((landmark) => landmark.id === activeLandmarkId) ||
    mapLandmarks[0]
  );

  useEffect(() => {
    if (!open || mapLandmarks.length === 0) {
      return;
    }
    const activeStillExists = mapLandmarks.some((landmark) => landmark.id === activeLandmarkId);
    if (!activeLandmarkId || !activeStillExists) {
      setActiveLandmarkId(mapLandmarks[0].id);
    }
  }, [activeLandmarkId, mapLandmarks, open]);

  useEffect(() => {
    if (!open) {
      clearGoogleMarkers(markersRef.current);
      markersRef.current = [];
      mapRef.current = null;
      boundsSignatureRef.current = '';
      setHoveredLandmarkId('');
      setActiveLandmarkId('');
      return;
    }

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open || !apiKey || mapLandmarks.length === 0 || !mapElementRef.current) {
      return undefined;
    }

    let cancelled = false;

    const drawMap = async () => {
      try {
        setLoadError('');
        const google = await loadGoogleMaps(apiKey);
        const { Map } = await google.maps.importLibrary('maps');
        const markerLibrary = mapId
          ? await google.maps.importLibrary('marker').catch(() => ({}))
          : {};
        const first = mapLandmarks[0];
        const map = mapRef.current || new Map(mapElementRef.current, {
          center: { lat: first.latitude, lng: first.longitude },
          zoom: 12,
          ...(mapId ? { mapId } : {}),
          streetViewControl: false,
          mapTypeControl: false,
          fullscreenControl: true,
        });

        if (cancelled) {
          return;
        }

        const shouldFitBounds = !mapRef.current;
        mapRef.current = map;
        clearGoogleMarkers(markersRef.current);

        const bounds = new google.maps.LatLngBounds();
        const nextMarkers = mapLandmarks.map((landmark) => {
          const isHighlighted = landmark.id === highlightedLandmarkId;
          const isSelected = selectedSet.has(landmark.id);
          const position = { lat: landmark.latitude, lng: landmark.longitude };
          bounds.extend(position);

          if (markerLibrary.AdvancedMarkerElement) {
            const marker = new markerLibrary.AdvancedMarkerElement({
              map,
              position,
              title: landmark.name,
              content: createMarkerContent(landmark, { isSelected, isHighlighted }),
              zIndex: isHighlighted ? 1000 : isSelected ? 500 : 100,
            });
            marker.addListener('click', () => setActiveLandmarkId(landmark.id));
            return marker;
          }

          const marker = new google.maps.Marker({
            map,
            position,
            title: landmark.name,
            label: isSelected ? 'OK' : '+',
            zIndex: isHighlighted ? 1000 : isSelected ? 500 : 100,
          });
          marker.addListener('click', () => setActiveLandmarkId(landmark.id));
          return marker;
        });

        const boundsSignature = mapLandmarks
          .map((landmark) => `${landmark.id}:${landmark.latitude}:${landmark.longitude}`)
          .join('|');
        markersRef.current = nextMarkers;

        if (shouldFitBounds || boundsSignatureRef.current !== boundsSignature) {
          map.fitBounds(bounds, 80);
          boundsSignatureRef.current = boundsSignature;
        } else if (activeLandmark) {
          map.panTo({ lat: activeLandmark.latitude, lng: activeLandmark.longitude });
        }
      } catch (error) {
        console.error('Google Maps load error:', error);
        if (!cancelled) {
          setLoadError('Nao foi possivel carregar o mapa.');
        }
      }
    };

    drawMap();

    return () => {
      cancelled = true;
      clearGoogleMarkers(markersRef.current);
      markersRef.current = [];
    };
  }, [activeLandmark, apiKey, highlightedLandmarkId, mapId, mapLandmarks, open, selectedSet]);

  if (!open) {
    return null;
  }

  const renderPlaceMedia = (landmark, size = 'large') => (
    <div
      className={cn(
        'shrink-0 overflow-hidden bg-muted',
        size === 'small' ? 'h-20 w-20 rounded-xl' : 'aspect-[4/3] rounded-2xl'
      )}
    >
      {landmark.image ? (
        <img src={landmark.image} alt={landmark.name} className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <MapPin className={cn('text-muted-foreground/45', size === 'small' ? 'h-6 w-6' : 'h-12 w-12')} />
        </div>
      )}
    </div>
  );

  return createPortal(
    <div className="fixed inset-0 z-50 bg-background text-foreground">
      <div className="flex h-full flex-col">
        <header className="flex items-center justify-between border-b border-border bg-background/95 px-4 py-3 backdrop-blur md:px-6">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary">
              Mapa da viagem
            </p>
            <h2 className="text-xl font-serif font-bold md:text-2xl">
              Explore os pontos e a distancia entre eles
            </h2>
          </div>
          <Button onClick={onClose} variant="outline" className="h-10 w-10 rounded-full p-0">
            <X className="h-5 w-5" />
          </Button>
        </header>

        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[430px_1fr]">
          <aside className="order-2 min-h-0 overflow-y-auto border-t border-border bg-background lg:order-1 lg:border-r lg:border-t-0">
            <div className="sticky top-0 z-10 space-y-4 border-b border-border bg-background/95 p-4 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-serif text-2xl font-bold">Pontos da regiao</h3>
                  <p className="text-sm font-medium text-muted-foreground">
                    Passe o mouse para localizar no mapa.
                  </p>
                </div>
                <Route className="h-5 w-5 shrink-0 text-secondary" />
              </div>

              <div className="flex rounded-full bg-muted p-1">
                {filterOptions.map((option) => {
                  const count = option.value === 'selected'
                    ? selectedCount
                    : option.value === 'suggested'
                      ? suggestedCount
                      : mapLandmarks.length;
                  const active = viewFilter === option.value;
                  return (
                    <button
                      type="button"
                      key={option.value}
                      onClick={() => setViewFilter(option.value)}
                      className={cn(
                        'flex-1 rounded-full px-3 py-2 text-xs font-bold transition-all',
                        active
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      )}
                    >
                      {option.label} <span className="text-[11px] opacity-70">{count}</span>
                    </button>
                  );
                })}
              </div>

              {onExploreMore && (
                <Button
                  onClick={onExploreMore}
                  disabled={isExploringMore}
                  className="w-full rounded-full bg-secondary py-6 font-bold text-white hover:bg-secondary/90"
                >
                  {isExploringMore ? (
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  ) : (
                    <Sparkles className="mr-2 h-5 w-5" />
                  )}
                  {isExploringMore ? 'Buscando mais pontos...' : 'Mostrar mais pontos turisticos'}
                </Button>
              )}

              {(exploreError || exploreNotice) && (
                <p
                  className={cn(
                    'rounded-2xl px-4 py-3 text-sm font-medium',
                    exploreError
                      ? 'bg-destructive/10 text-destructive'
                      : 'bg-primary/10 text-primary'
                  )}
                >
                  {exploreError || exploreNotice}
                </p>
              )}
            </div>

            <div className="space-y-3 p-4">
              {filteredLandmarks.map((landmark) => {
                const itemSelected = selectedSet.has(landmark.id);
                const itemActive = activeLandmark?.id === landmark.id;
                const itemHighlighted = hoveredLandmarkId === landmark.id;

                return (
                  <div
                    key={landmark.id}
                    onMouseEnter={() => setHoveredLandmarkId(landmark.id)}
                    onMouseLeave={() => setHoveredLandmarkId('')}
                    className={cn(
                      'rounded-2xl border bg-card p-3 shadow-sm transition-all',
                      itemActive || itemHighlighted
                        ? 'border-primary bg-primary/5 shadow-md'
                        : 'border-border hover:border-primary/40 hover:bg-muted/30'
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => setActiveLandmarkId(landmark.id)}
                      className="flex w-full gap-3 text-left"
                    >
                      {renderPlaceMedia(landmark, 'small')}
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="truncate font-bold">{landmark.name}</p>
                            <p className="truncate text-xs font-medium text-muted-foreground">
                              {[landmark.city, landmark.country].filter(Boolean).join(', ')}
                            </p>
                          </div>
                          <Badge
                            className={cn(
                              'shrink-0 rounded-full text-[11px]',
                              itemSelected ? 'bg-primary text-white' : 'bg-secondary text-white'
                            )}
                          >
                            {itemSelected ? 'No roteiro' : 'Sugerido'}
                          </Badge>
                        </div>
                        {landmark.description && (
                          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                            {landmark.description}
                          </p>
                        )}
                        <div className="mt-2 flex flex-wrap gap-2">
                          {landmark.duration_minutes && (
                            <span className="inline-flex items-center rounded-full bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground">
                              <Clock3 className="mr-1 h-3 w-3" />
                              {landmark.duration_minutes} min
                            </span>
                          )}
                          {landmark.categories?.slice(0, 2).map((category) => (
                            <span
                              key={category}
                              className="rounded-full bg-muted px-2 py-1 text-[11px] font-bold text-muted-foreground"
                            >
                              {category}
                            </span>
                          ))}
                        </div>
                      </div>
                    </button>

                    <div className="mt-3 flex gap-2">
                      <Button
                        onClick={() => onToggleLandmark(landmark.id)}
                        variant={itemSelected ? 'outline' : 'default'}
                        className={cn(
                          'h-9 flex-1 rounded-full text-xs font-bold',
                          itemSelected ? '' : 'bg-primary text-white hover:bg-primary/90'
                        )}
                      >
                        {itemSelected ? (
                          <>
                            <Check className="mr-1.5 h-4 w-4" />
                            Remover
                          </>
                        ) : (
                          <>
                            <Plus className="mr-1.5 h-4 w-4" />
                            Adicionar
                          </>
                        )}
                      </Button>
                      {landmark.maps_url && (
                        <Button
                          asChild
                          variant="outline"
                          className="h-9 w-9 rounded-full p-0"
                        >
                          <a href={landmark.maps_url} target="_blank" rel="noreferrer" aria-label={`Abrir ${landmark.name} no Google Maps`}>
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}

              {filteredLandmarks.length === 0 && (
                <div className="rounded-2xl border border-dashed border-border p-6 text-center">
                  <MapPin className="mx-auto mb-3 h-8 w-8 text-muted-foreground/40" />
                  <p className="font-bold">Nenhum ponto neste filtro.</p>
                  <p className="text-sm text-muted-foreground">
                    Troque o filtro ou busque mais pontos para ampliar a selecao.
                  </p>
                </div>
              )}
            </div>
          </aside>

          <section className="relative order-1 min-h-[420px] bg-muted lg:order-2">
            {apiKey && mapLandmarks.length > 0 && !loadError && (
              <div ref={mapElementRef} className="h-full min-h-[420px] w-full" />
            )}

            {!apiKey && (
              <div className="flex h-full min-h-[420px] items-center justify-center p-8 text-center">
                <div className="max-w-md rounded-2xl border border-border bg-background p-6 shadow-sm">
                  <MapPin className="mx-auto mb-4 h-10 w-10 text-primary" />
                  <h3 className="mb-2 text-xl font-serif font-bold">Mapa nao configurado</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    Configure `VITE_GOOGLE_MAPS_BROWSER_KEY` no frontend para ativar o mapa embutido.
                  </p>
                </div>
              </div>
            )}

            {apiKey && mapLandmarks.length === 0 && (
              <div className="flex h-full min-h-[420px] items-center justify-center p-8 text-center">
                <div className="max-w-md rounded-2xl border border-border bg-background p-6 shadow-sm">
                  <MapPin className="mx-auto mb-4 h-10 w-10 text-secondary" />
                  <h3 className="mb-2 text-xl font-serif font-bold">Sem coordenadas ainda</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">
                    O mapa aparece quando os locais retornam com latitude e longitude.
                  </p>
                </div>
              </div>
            )}

            {loadError && (
              <div className="flex h-full min-h-[420px] items-center justify-center p-8 text-center">
                <div className="max-w-md rounded-2xl border border-border bg-background p-6 shadow-sm">
                  <MapPin className="mx-auto mb-4 h-10 w-10 text-destructive" />
                  <h3 className="mb-2 text-xl font-serif font-bold">Erro ao carregar mapa</h3>
                  <p className="text-sm leading-relaxed text-muted-foreground">{loadError}</p>
                </div>
              </div>
            )}

            <div className="absolute left-4 top-4 rounded-full bg-background/90 px-4 py-2 text-sm font-bold shadow-sm backdrop-blur">
              {mapLandmarks.length} pontos no mapa
            </div>

            {activeLandmark && (
              <div className="absolute bottom-4 left-4 right-4 max-w-xl rounded-2xl border border-border bg-background/95 p-4 shadow-xl backdrop-blur md:right-auto md:w-[420px]">
                <div className="flex gap-3">
                  {renderPlaceMedia(activeLandmark, 'small')}
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary">
                      {activeLandmark.city}
                    </p>
                    <h3 className="truncate text-lg font-serif font-bold">{activeLandmark.name}</h3>
                    {activeLandmark.description && (
                      <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-muted-foreground">
                        {activeLandmark.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>,
    document.body
  );
};

export default MapOverviewModal;
