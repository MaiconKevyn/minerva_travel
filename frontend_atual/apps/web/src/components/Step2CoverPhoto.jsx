
import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, UploadCloud, CheckCircle2 } from 'lucide-react';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import {
  deriveExpectedFamilyMemberCount,
  normalizeFamilyMemberCount,
} from '@/utils/guide-form.js';

const Step2CoverPhoto = () => {
  const {
    coverPhoto,
    coverPhotoUrl,
    updateCoverPhoto,
    expectedCoverFamilyMemberCount,
    updateExpectedCoverFamilyMemberCount,
    childrenList,
    parentsList,
    nextStep
  } = useConversationalGuide();
  const [isDragging, setIsDragging] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const fileInputRef = useRef(null);
  const derivedFamilyMemberCount = deriveExpectedFamilyMemberCount({ childrenList, parentsList });
  const confirmedFamilyMemberCount = normalizeFamilyMemberCount(expectedCoverFamilyMemberCount);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      updateCoverPhoto(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      updateCoverPhoto(e.target.files[0]);
    }
  };

  const handleConfirm = () => {
    if (!coverPhoto || confirmedFamilyMemberCount <= 0) return;
    setIsConfirmed(true);
  };

  const handleFamilyMemberCountChange = (event) => {
    updateExpectedCoverFamilyMemberCount(event.target.value);
  };

  useEffect(() => {
    if (coverPhoto && confirmedFamilyMemberCount <= 0 && derivedFamilyMemberCount > 0) {
      updateExpectedCoverFamilyMemberCount(derivedFamilyMemberCount);
    }
  }, [
    coverPhoto,
    confirmedFamilyMemberCount,
    derivedFamilyMemberCount,
    updateExpectedCoverFamilyMemberCount,
  ]);

  useEffect(() => {
    if (isConfirmed) {
      const timer = setTimeout(() => {
        nextStep();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isConfirmed, nextStep]);

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col items-center justify-center min-h-[50vh]">
      <AnimatePresence mode="wait">
        {!isConfirmed ? (
          <motion.div
            key="upload"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="w-full text-center space-y-8"
          >
            <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground leading-tight">
              Seu roteiro está pronto. Escolha a foto de capa do PDF
            </h2>
            <p className="text-lg text-muted-foreground">
              Essa imagem abre o livrinho da família antes das atividades, mapas e memórias da viagem.
            </p>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative cursor-pointer overflow-hidden rounded-3xl border-4 border-dashed transition-all duration-300 aspect-[16/9] md:aspect-[21/9] flex flex-col items-center justify-center group ${
                isDragging ? 'border-primary bg-primary/5 scale-[1.02]' : 'border-border/60 hover:border-primary/50 hover:bg-muted/30'
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept="image/*"
                className="hidden"
              />

              {coverPhotoUrl ? (
                <>
                  <img src={coverPhotoUrl} alt="Capa" className="absolute inset-0 w-full h-full object-cover" />
                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                    <p className="text-white font-bold text-lg">Trocar Foto</p>
                  </div>
                </>
              ) : (
                <div className="text-center p-6">
                  <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-4 text-primary">
                    <UploadCloud className="w-10 h-10" />
                  </div>
                  <p className="font-bold text-xl text-foreground mb-2">Clique ou arraste uma foto aqui</p>
                  <p className="text-muted-foreground">PNG, JPG ou WEBP até 10MB</p>
                </div>
              )}
            </div>

            <div className="mx-auto max-w-xl rounded-2xl border border-border/70 bg-card p-4 text-left shadow-sm">
              <label htmlFor="expected-cover-family-count" className="text-sm font-bold text-foreground">
                Quantas pessoas aparecem na foto?
              </label>
              <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center">
                <input
                  id="expected-cover-family-count"
                  type="number"
                  min="1"
                  max="20"
                  value={confirmedFamilyMemberCount || ''}
                  onChange={handleFamilyMemberCountChange}
                  placeholder={derivedFamilyMemberCount ? String(derivedFamilyMemberCount) : '4'}
                  className="h-12 w-full rounded-xl border border-border bg-background px-4 text-base font-semibold text-foreground outline-none transition focus:border-primary sm:w-32"
                />
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Se a ilustração não preservar todo mundo, usamos uma capa segura com a foto original.
                </p>
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: coverPhoto ? 1 : 0 }}
              className="flex justify-center"
            >
              <Button
                onClick={handleConfirm}
                disabled={!coverPhoto || confirmedFamilyMemberCount <= 0}
              className="w-full rounded-full bg-primary px-8 py-6 text-lg font-bold text-white shadow-lg transition-all hover:-translate-y-1 hover:bg-primary/90 sm:w-auto"
            >
                Continuar para revisão <ArrowRight className="ml-2 w-5 h-5" />
              </Button>
            </motion.div>
          </motion.div>
        ) : (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center space-y-6"
          >
            <div className="relative w-32 h-32 mx-auto">
              <img src={coverPhotoUrl} alt="Capa confirmada" className="w-full h-full object-cover rounded-full shadow-xl" />
              <div className="absolute -bottom-2 -right-2 bg-background rounded-full p-1 shadow-sm">
                <CheckCircle2 className="w-8 h-8 text-primary" />
              </div>
            </div>
            <h2 className="text-3xl md:text-4xl font-serif font-bold text-foreground">
              Capa escolhida!
            </h2>
            {confirmedFamilyMemberCount > 0 && (
              <p className="text-muted-foreground">
                Vamos preservar {confirmedFamilyMemberCount} pessoa{confirmedFamilyMemberCount === 1 ? '' : 's'} na capa.
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Step2CoverPhoto;
