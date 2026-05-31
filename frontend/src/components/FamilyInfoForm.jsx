import React from 'react';
import { CalendarDays, Plus, X, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { motion, AnimatePresence } from 'framer-motion';
import WarmCard from './WarmCard.jsx';
import { Sun } from './DecorativeElements.jsx';

const FamilyInfoForm = ({
  title,
  onTitleChange,
  year,
  onYearChange,
  parents,
  onParentsChange,
  childrenNames,
  onChildrenChange,
  errors,
}) => {
  const addChild = () => {
    onChildrenChange([...childrenNames, '']);
  };

  const removeChild = (index) => {
    const newChildren = childrenNames.filter((_, i) => i !== index);
    onChildrenChange(newChildren.length > 0 ? newChildren : ['']);
  };

  const updateChild = (index, value) => {
    const newChildren = [...childrenNames];
    newChildren[index] = value;
    onChildrenChange(newChildren);
  };

  const addParent = () => {
    onParentsChange([...parents, '']);
  };

  const removeParent = (index) => {
    const newParents = parents.filter((_, i) => i !== index);
    onParentsChange(newParents.length > 0 ? newParents : ['']);
  };

  const updateParent = (index, value) => {
    const newParents = [...parents];
    newParents[index] = value;
    onParentsChange(newParents);
  };

  return (
    <WarmCard className="border-t-4 border-t-secondary relative">
      <Sun className="absolute -bottom-6 -right-6 w-24 h-24 text-primary/10 rotate-12" />

      <div className="mb-8">
        <h3 className="text-3xl font-serif font-bold mb-2 flex items-center gap-3">
          <Users className="w-8 h-8 text-secondary" />
          Sobre a Viagem
        </h3>
        <p className="text-muted-foreground text-lg">Dados que aparecem na capa, introducao e carta final.</p>
      </div>

      <div className="space-y-8">
        <div className="grid gap-5 md:grid-cols-[1fr_160px]">
          <div className="space-y-3">
            <Label htmlFor="guideTitle" className="text-base font-medium">Titulo do guia</Label>
            <Input
              id="guideTitle"
              type="text"
              value={title}
              onChange={(e) => onTitleChange(e.target.value)}
              className="h-14 rounded-2xl text-lg px-5 bg-background border-border focus-visible:ring-secondary focus-visible:border-secondary transition-all"
            />
            {errors.title && <InlineError>{errors.title}</InlineError>}
          </div>

          <div className="space-y-3">
            <Label htmlFor="tripYear" className="text-base font-medium flex items-center gap-2">
              <CalendarDays className="w-4 h-4 text-secondary" />
              Ano
            </Label>
            <Input
              id="tripYear"
              type="number"
              min="2024"
              max="2100"
              value={year}
              onChange={(e) => onYearChange(e.target.value)}
              className="h-14 rounded-2xl text-lg px-5 bg-background border-border focus-visible:ring-secondary focus-visible:border-secondary transition-all"
            />
            {errors.year && <InlineError>{errors.year}</InlineError>}
          </div>
        </div>

        <PeopleList
          label="Criancas"
          addLabel="Adicionar Crianca"
          placeholder="Nome da crianca"
          values={childrenNames}
          onAdd={addChild}
          onRemove={removeChild}
          onUpdate={updateChild}
          accent="secondary"
        />
        {errors.children && <InlineError>{errors.children}</InlineError>}

        <PeopleList
          label="Pais ou responsaveis"
          addLabel="Adicionar Responsavel"
          placeholder="Nome do responsavel"
          values={parents}
          onAdd={addParent}
          onRemove={removeParent}
          onUpdate={updateParent}
          accent="primary"
        />
        {errors.parents && <InlineError>{errors.parents}</InlineError>}
      </div>
    </WarmCard>
  );
};

function PeopleList({ label, addLabel, placeholder, values, onAdd, onRemove, onUpdate, accent }) {
  const accentClass = accent === 'primary' ? 'text-primary border-primary/30 hover:bg-primary' : 'text-secondary border-secondary/30 hover:bg-secondary';
  const ringClass = accent === 'primary' ? 'focus-visible:ring-primary' : 'focus-visible:ring-secondary';

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Label className="text-base font-medium">{label}</Label>
        <Button
          type="button"
          variant="outline"
          onClick={onAdd}
          className={`rounded-full hover:text-white transition-all duration-200 active:scale-95 ${accentClass}`}
        >
          <Plus className="w-4 h-4 mr-2" />
          {addLabel}
        </Button>
      </div>

      <AnimatePresence mode="popLayout">
        {values.map((value, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: -20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="flex gap-3 items-center bg-muted/40 p-2 rounded-2xl"
          >
            <div className="w-10 h-10 bg-white rounded-full flex items-center justify-center font-serif font-bold text-secondary shadow-sm">
              {index + 1}
            </div>
            <Input
              type="text"
              placeholder={`${placeholder} ${index + 1}`}
              value={value}
              onChange={(e) => onUpdate(index, e.target.value)}
              className={`flex-1 h-12 rounded-xl bg-white border-transparent ${ringClass}`}
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              onClick={() => onRemove(index)}
              className="rounded-full hover:bg-destructive/10 hover:text-destructive w-10 h-10 mr-1 transition-colors"
            >
              <X className="w-5 h-5" />
            </Button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

function InlineError({ children }) {
  return (
    <p className="text-sm font-medium text-destructive bg-destructive/10 py-1.5 px-3 rounded-lg inline-block">
      {children}
    </p>
  );
}

export default FamilyInfoForm;
