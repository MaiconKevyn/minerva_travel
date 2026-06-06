
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Map as MapIcon, MapPin } from 'lucide-react';
import { cn } from '@/lib/utils';
import { landmarkMapAction } from '@/utils/minerva-api.js';
import PlaceMapModal from './PlaceMapModal.jsx';

const LandmarkCard = ({
  // Showcase Mode Props (from landmarks.js)
  id, number, image, city, name, curiosity, description,
  // Selection Mode Props (from Step4Attractions.jsx)
  landmark, destination, isSelected, onToggle, index = 0
}) => {
  const [isMapOpen, setIsMapOpen] = useState(false);
  // Determine the mode: if onToggle exists, it's used in the Guide Creator (Selection Mode)
  const isSelectionMode = !!onToggle;

  // Normalize the data based on the mode
  const data = isSelectionMode ? landmark : { id, number, image, city, name, curiosity, description };
  const displayCity = isSelectionMode ? (destination?.city || data.city) : data.city;
  const photoAttribution = data.image_attributions?.find?.(
    (attribution) => attribution.display_name || attribution.uri
  );
  const normalizedLandmark = {
    ...data,
    city: displayCity,
    country: destination?.country || data.country,
  };
  const mapAction = landmarkMapAction(normalizedLandmark);
  const mapsUrl = mapAction.mapsUrl;
  const canOpenEmbeddedMap = mapAction.mode === 'embedded';
  const isMentionedPlace = isSelectionMode && data.source_type === 'mentioned';
  const sourceTone = !isSelectionMode || isMentionedPlace ? 'primary' : 'secondary';

  const openEmbeddedMap = (event) => {
    event.stopPropagation();
    setIsMapOpen(true);
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-50px" }}
        transition={{ duration: 0.4, delay: index * 0.1 }}
        onClick={() => isSelectionMode && onToggle(data.id)}
        className={cn(
          "group relative rounded-3xl overflow-hidden transition-all duration-300 border bg-card dark:bg-slate-800 flex flex-col h-full",
          isSelectionMode ? "cursor-pointer" : "cursor-default",
          isSelectionMode && isMentionedPlace && !isSelected
            ? "border-primary/35 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-primary/70"
            : isSelectionMode && !isMentionedPlace && !isSelected
              ? "border-secondary/35 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-secondary/70"
              : isSelected && isMentionedPlace
                ? "border-primary shadow-[0_8px_30px_rgb(241,97,59,0.15)] scale-[1.02]"
                : isSelected
                  ? "border-secondary shadow-[0_8px_30px_rgb(72,156,200,0.15)] scale-[1.02]"
                  : "border-border/60 dark:border-slate-700 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:border-primary/30"
        )}
      >
        {/* Top Image Header */}
        <div className="relative w-full h-56 overflow-hidden bg-muted">
          {data.image ? (
            <img
              src={data.image}
              alt={data.name}
              className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-secondary/10">
              <MapPin className="w-12 h-12 text-secondary/30" />
            </div>
          )}

          {/* Subtle gradient overlay for better text contrast if we had text, and depth */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {canOpenEmbeddedMap ? (
            <button
              type="button"
              title={`Ver ${data.name} no mapa`}
              aria-label={`Ver ${data.name} no mapa`}
              onClick={openEmbeddedMap}
              className="absolute left-4 top-4 z-10 h-9 w-9 rounded-full bg-background/85 text-secondary shadow-sm backdrop-blur-sm border border-white/40 flex items-center justify-center transition-all hover:bg-background hover:text-primary hover:scale-105"
            >
              <MapIcon className="h-4 w-4" />
            </button>
          ) : mapsUrl ? (
            <a
              href={mapsUrl}
              target="_blank"
              rel="noreferrer"
              title={`Abrir ${data.name} no mapa`}
              aria-label={`Abrir ${data.name} no mapa`}
              onClick={(event) => event.stopPropagation()}
              className="absolute left-4 top-4 z-10 h-9 w-9 rounded-full bg-background/85 text-secondary shadow-sm backdrop-blur-sm border border-white/40 flex items-center justify-center transition-all hover:bg-background hover:text-primary hover:scale-105"
            >
              <MapIcon className="h-4 w-4" />
            </a>
          ) : null}

        {photoAttribution && (
          <div className="absolute left-3 bottom-3 z-10 max-w-[calc(100%-1.5rem)] rounded-full bg-black/55 backdrop-blur-sm px-3 py-1 text-[10px] font-medium text-white/90">
            Foto:{' '}
            {photoAttribution.uri ? (
              <a
                href={photoAttribution.uri}
                target="_blank"
                rel="noreferrer"
                onClick={(event) => event.stopPropagation()}
                className="underline decoration-white/50 underline-offset-2"
              >
                {photoAttribution.display_name || 'Google Places'}
              </a>
            ) : (
              <span>{photoAttribution.display_name}</span>
            )}
          </div>
        )}

        {/* Number Badge (Showcase Mode) */}
        {!isSelectionMode && data.number && (
          <div className="absolute top-4 right-4 w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center font-bold text-lg shadow-lg z-10">
            {data.number}
          </div>
        )}

        {/* Checkbox Indicator (Selection Mode) */}
        {isSelectionMode && (
          <div className="absolute top-4 right-4 z-10">
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm border-2",
              isSelected
                ? sourceTone === 'primary'
                  ? "bg-primary border-primary text-white scale-110"
                  : "bg-secondary border-secondary text-white scale-110"
                : sourceTone === 'primary'
                  ? "bg-background/80 backdrop-blur-sm border-primary/30 text-transparent group-hover:border-primary/70"
                  : "bg-background/80 backdrop-blur-sm border-secondary/30 text-transparent group-hover:border-secondary/70"
            )}>
              <Check className={cn("w-4 h-4 transition-opacity", isSelected ? "opacity-100" : "opacity-0")} />
            </div>
          </div>
        )}
        </div>

        <div className="p-6 flex flex-col flex-1">
          {/* City & Location */}
          <div className="mb-2">
            <span className={cn(
              "text-xs font-bold tracking-widest uppercase flex items-center gap-1.5",
              sourceTone === 'primary' ? "text-primary" : "text-secondary"
            )}>
              <MapPin className="w-3.5 h-3.5" />
              {displayCity}
            </span>
          </div>

          {/* Title */}
          <h4 className="text-2xl font-serif font-bold text-secondary dark:text-secondary-foreground mb-4 leading-tight group-hover:text-primary transition-colors">
            {data.name}
          </h4>

          {/* Curiosity / Fun Fact (Showcase Mode) */}
          {data.curiosity && (
            <div className="mb-4 p-3 bg-muted/50 dark:bg-slate-900/50 rounded-xl border-l-4 border-accent">
              <p className="text-sm italic text-muted-foreground font-medium">
                "{data.curiosity}"
              </p>
            </div>
          )}

          {/* Description */}
          <p className="text-foreground/80 dark:text-gray-300 text-sm leading-relaxed flex-1">
            {data.description || 'Um ponto turístico imperdível para sua viagem em família.'}
          </p>
        </div>
      </motion.div>

      <PlaceMapModal
        open={isMapOpen}
        landmark={normalizedLandmark}
        mapsUrl={mapsUrl}
        isSelected={isSelected}
        onToggle={isSelectionMode ? onToggle : null}
        onClose={() => setIsMapOpen(false)}
      />
    </>
  );
};

export default LandmarkCard;
