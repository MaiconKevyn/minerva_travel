
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Users, Baby, Calendar, Home, Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { useConversationalGuide } from '@/contexts/ConversationalGuideContext.jsx';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  createGuideItemId,
  MAX_GUIDE_CHILDREN,
  MAX_GUIDE_PARENTS,
  validGuideChildren,
} from '@/utils/guide-form.js';

const generateId = () => createGuideItemId('family-member');
const childInputId = (childId, field) => `child-${childId}-${field}`;
const parentInputId = (parentId) => `parent-${parentId}-name`;

const validationMessages = {
  familyName: 'Adicione o nome da família.',
  children: 'Adicione pelo menos uma criança com nome e idade.',
  incompleteChildren: 'Informe nome e idade de cada criança adicionada.',
  parents: 'Adicione pelo menos um responsável.',
};

const EnhancedStep5FamilyDetails = () => {
  const {
    familyName,
    updateFamilyName,
    childrenList: contextChildren,
    setChildrenList,
    parentsList: contextParents,
    setParentsList,
    year,
    setYear,
    nextStep
  } = useConversationalGuide();

  const [localFamilyName, setLocalFamilyName] = useState(familyName || '');
  const [validationError, setValidationError] = useState('');

  // Initialize local state with context data or defaults
  const [children, setChildren] = useState(() => (
    contextChildren.length > 0
      ? contextChildren.slice(0, MAX_GUIDE_CHILDREN).map(child =>
          typeof child === 'string'
            ? { id: generateId(), name: child, age: '' }
            : { id: child.id || generateId(), name: child.name || '', age: child.age || '' }
        )
      : [{ id: generateId(), name: '', age: '' }]
  ));

  const [parents, setParents] = useState(() => (
    contextParents.length > 0
      ? contextParents
        .slice(0, MAX_GUIDE_PARENTS)
        .map(name => ({ id: generateId(), name }))
      : [{ id: generateId(), name: '' }]
  ));

  const clearValidationError = () => setValidationError('');

  const showValidationError = (message, focusTargetId) => {
    setValidationError(message);
    document.getElementById(focusTargetId)?.focus();
  };

  const handleAddChild = () => {
    if (children.length < MAX_GUIDE_CHILDREN) {
      setChildren((current) => [
        ...current,
        { id: generateId(), name: '', age: '' },
      ]);
      clearValidationError();
    }
  };

  const handleRemoveChild = (id) => {
    if (children.length > 1) {
      setChildren((current) => current.filter(c => c.id !== id));
      clearValidationError();
      toast.success('Criança removida', {
        description: 'A lista foi atualizada.',
        duration: 2000,
      });
    }
  };

  const handleChildChange = (id, field, value) => {
    setChildren((current) => (
      current.map(c => c.id === id ? { ...c, [field]: value } : c)
    ));
    clearValidationError();
  };

  const handleAddParent = () => {
    if (parents.length < MAX_GUIDE_PARENTS) {
      setParents((current) => [...current, { id: generateId(), name: '' }]);
      clearValidationError();
    }
  };

  const handleRemoveParent = (id) => {
    if (parents.length > 1) {
      setParents((current) => current.filter(p => p.id !== id));
      clearValidationError();
      toast.success('Responsável removido', {
        description: 'A lista foi atualizada.',
        duration: 2000,
      });
    }
  };

  const handleParentChange = (id, value) => {
    setParents((current) => (
      current.map(p => p.id === id ? { ...p, name: value } : p)
    ));
    clearValidationError();
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    const normalizedFamilyName = localFamilyName.trim();
    const touchedChildren = children.filter(c => c.name.trim() !== '' || String(c.age || '').trim() !== '');
    const validChildren = validGuideChildren(children);
    const validParents = parents.filter(p => p.name.trim() !== '');

    if (!normalizedFamilyName) {
      showValidationError(validationMessages.familyName, 'familyName');
      return;
    }

    if (validChildren.length === 0) {
      const firstIncompleteChild = touchedChildren[0] || children[0];
      const firstIncompleteField = firstIncompleteChild.name.trim() ? 'age' : 'name';
      showValidationError(
        validationMessages.children,
        childInputId(firstIncompleteChild.id, firstIncompleteField),
      );
      return;
    }

    if (touchedChildren.length !== validChildren.length) {
      const incompleteChild = touchedChildren.find((child) => (
        !child.name.trim() || !(Number.parseInt(child.age, 10) > 0)
      ));
      const incompleteField = incompleteChild?.name.trim() ? 'age' : 'name';
      showValidationError(
        validationMessages.incompleteChildren,
        childInputId(incompleteChild?.id || children[0].id, incompleteField),
      );
      return;
    }

    if (validParents.length === 0) {
      showValidationError(validationMessages.parents, parentInputId(parents[0].id));
      return;
    }

    // Save to context
    updateFamilyName(normalizedFamilyName);
    setChildrenList(validChildren);
    setParentsList(validParents.map(p => p.name.trim()));

    clearValidationError();
    nextStep();
  };

  return (
    <div className="w-full max-w-3xl mx-auto flex flex-col min-h-[60vh] justify-center py-4">
      <div className="text-center space-y-4 mb-12">
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-serif font-bold text-foreground">
          Detalhes da Família
        </h2>
        <p className="text-lg sm:text-xl text-muted-foreground font-medium">
          Para deixar o guia ainda mais especial, conte-nos quem vai aparecer nessa aventura.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Family Name Section */}
        <div className="bg-card dark:bg-slate-800/50 p-6 md:p-8 rounded-[2rem] shadow-sm border-2 border-accent/10">
          <Label htmlFor="familyName" className="mb-6 flex items-center gap-3 text-lg font-bold text-foreground sm:text-xl">
            <div className="p-2 bg-accent/10 rounded-xl text-accent">
              <Home className="w-6 h-6" />
            </div>
            Nome da Família
          </Label>
          <Input
            id="familyName"
            value={localFamilyName}
            onChange={(e) => {
              setLocalFamilyName(e.target.value);
              clearValidationError();
            }}
            placeholder="Ex: Silva, Oliveira, The Smiths..."
            aria-invalid={validationError === validationMessages.familyName}
            aria-describedby={
              validationError === validationMessages.familyName
                ? 'family-name-error'
                : undefined
            }
            className="rounded-xl border-border bg-background py-6 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-accent sm:text-lg"
          />
          {validationError === validationMessages.familyName && (
            <p
              id="family-name-error"
              role="alert"
              aria-live="assertive"
              className="mt-3 text-sm font-bold text-destructive"
            >
              {validationError}
            </p>
          )}
        </div>

        {/* Children Section */}
        <div className="bg-card dark:bg-slate-800/50 p-6 md:p-8 rounded-[2rem] shadow-sm border-2 border-primary/10">
          <div className="flex items-center justify-between mb-6">
            <Label className="flex items-center gap-3 text-lg font-bold text-foreground sm:text-xl">
              <div className="p-2 bg-primary/10 rounded-xl text-primary">
                <Baby className="w-6 h-6" />
              </div>
              Crianças
            </Label>
            <span className="text-sm font-medium text-muted-foreground bg-muted px-3 py-1 rounded-full">
              {children.length} de {MAX_GUIDE_CHILDREN}
            </span>
          </div>

          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {children.map((child, index) => (
                <motion.div
                  key={child.id}
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginBottom: 12 }}
                  exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                  transition={{ duration: 0.2 }}
                  className="grid grid-cols-[1fr_110px_auto] items-center gap-3"
                >
                  <Input
                    id={childInputId(child.id, 'name')}
                    value={child.name}
                    onChange={(e) => handleChildChange(child.id, 'name', e.target.value)}
                    placeholder={`Nome da criança ${index + 1}`}
                    aria-label={`Nome da criança ${index + 1}`}
                    aria-invalid={Boolean(
                      (validationError === validationMessages.children ||
                        validationError === validationMessages.incompleteChildren) &&
                      !child.name.trim()
                    )}
                    aria-describedby={
                      validationError === validationMessages.children ||
                      validationError === validationMessages.incompleteChildren
                        ? 'children-error'
                        : undefined
                    }
                    className="rounded-xl border-border bg-background py-6 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-primary sm:text-lg"
                  />
                  <Input
                    id={childInputId(child.id, 'age')}
                    type="number"
                    min="1"
                    max="17"
                    value={child.age}
                    onChange={(e) => handleChildChange(child.id, 'age', e.target.value)}
                    placeholder="Idade"
                    aria-label={`Idade da criança ${index + 1}`}
                    aria-invalid={Boolean(
                      (validationError === validationMessages.children ||
                        validationError === validationMessages.incompleteChildren) &&
                      !(Number.parseInt(child.age, 10) > 0)
                    )}
                    aria-describedby={
                      validationError === validationMessages.children ||
                      validationError === validationMessages.incompleteChildren
                        ? 'children-error'
                        : undefined
                    }
                    className="rounded-xl border-border bg-background py-6 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-primary sm:text-lg"
                  />
                  {children.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveChild(child.id)}
                      className="shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-xl h-12 w-12"
                      aria-label={`Remover criança ${index + 1}`}
                    >
                      <X className="w-5 h-5" />
                    </Button>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {(validationError === validationMessages.children ||
            validationError === validationMessages.incompleteChildren) && (
            <p
              id="children-error"
              role="alert"
              aria-live="assertive"
              className="mt-3 text-sm font-bold text-destructive"
            >
              {validationError}
            </p>
          )}

          <Button
            type="button"
            variant="outline"
            onClick={handleAddChild}
            disabled={children.length >= MAX_GUIDE_CHILDREN}
            className="w-full mt-4 py-6 rounded-xl border-dashed border-2 hover:border-primary hover:bg-primary/5 text-muted-foreground hover:text-primary transition-colors"
          >
            <Plus className="w-5 h-5 mr-2" />
            Adicionar Criança
          </Button>
        </div>

        {/* Parents Section */}
        <div className="bg-card dark:bg-slate-800/50 p-6 md:p-8 rounded-[2rem] shadow-sm border-2 border-secondary/10">
          <div className="flex items-center justify-between mb-6">
            <Label className="flex items-center gap-3 text-lg font-bold text-foreground sm:text-xl">
              <div className="p-2 bg-secondary/10 rounded-xl text-secondary">
                <Users className="w-6 h-6" />
              </div>
              Responsáveis
            </Label>
            <span className="text-sm font-medium text-muted-foreground bg-muted px-3 py-1 rounded-full">
              {parents.length} de {MAX_GUIDE_PARENTS}
            </span>
          </div>

          <div className="space-y-3">
            <AnimatePresence initial={false}>
              {parents.map((parent, index) => (
                <motion.div
                  key={parent.id}
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginBottom: 12 }}
                  exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                  transition={{ duration: 0.2 }}
                  className="flex items-center gap-3"
                >
                  <Input
                    id={parentInputId(parent.id)}
                    value={parent.name}
                    onChange={(e) => handleParentChange(parent.id, e.target.value)}
                    placeholder={`Nome do responsável ${index + 1}`}
                    aria-label={`Nome do responsável ${index + 1}`}
                    aria-invalid={Boolean(
                      validationError === validationMessages.parents && !parent.name.trim()
                    )}
                    aria-describedby={
                      validationError === validationMessages.parents
                        ? 'parents-error'
                        : undefined
                    }
                    className="rounded-xl border-border bg-background py-6 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-secondary sm:text-lg"
                  />
                  {parents.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveParent(parent.id)}
                      className="shrink-0 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-xl h-12 w-12"
                      aria-label={`Remover responsável ${index + 1}`}
                    >
                      <X className="w-5 h-5" />
                    </Button>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {validationError === validationMessages.parents && (
            <p
              id="parents-error"
              role="alert"
              aria-live="assertive"
              className="mt-3 text-sm font-bold text-destructive"
            >
              {validationError}
            </p>
          )}

          <Button
            type="button"
            variant="outline"
            onClick={handleAddParent}
            disabled={parents.length >= MAX_GUIDE_PARENTS}
            className="w-full mt-4 py-6 rounded-xl border-dashed border-2 hover:border-secondary hover:bg-secondary/5 text-muted-foreground hover:text-secondary transition-colors"
          >
            <Plus className="w-5 h-5 mr-2" />
            Adicionar Responsável
          </Button>
        </div>

        {/* Year Section */}
        <div className="bg-card dark:bg-slate-800/50 p-6 md:p-8 rounded-[2rem] shadow-sm border-2 border-accent/10">
          <Label htmlFor="year" className="mb-6 flex items-center gap-3 text-lg font-bold text-foreground sm:text-xl">
            <div className="p-2 bg-accent/10 rounded-xl text-accent">
              <Calendar className="w-6 h-6" />
            </div>
            Ano da Viagem
          </Label>
          <Input
            id="year"
            type="number"
            value={year}
            onChange={(e) => setYear(parseInt(e.target.value) || new Date().getFullYear())}
            placeholder="Ex: 2026"
            className="rounded-xl border-border bg-background py-6 text-base text-foreground placeholder:text-muted-foreground focus-visible:ring-accent sm:text-lg"
          />
        </div>

        <div className="pt-8 flex justify-center">
          <Button
            type="submit"
            className="w-full max-w-md rounded-full bg-primary px-6 py-6 text-base font-bold text-white shadow-xl transition-all hover:-translate-y-1 hover:bg-primary/90 sm:w-auto sm:px-12 sm:py-8 sm:text-xl"
          >
            Continuar <ArrowRight className="ml-3 w-6 h-6" />
          </Button>
        </div>
      </form>
    </div>
  );
};

export default EnhancedStep5FamilyDetails;
