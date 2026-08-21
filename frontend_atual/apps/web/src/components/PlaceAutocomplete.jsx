import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import { Check, Loader2, MapPin } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { fetchPlaceSuggestions } from '@/utils/minerva-api.js';

const DEBOUNCE_MS = 300;

/**
 * Campo de lugar com sugestões oficiais do Google Places.
 *
 * O motivo de existir: como texto livre, "Torre Eifel" era aceito e o erro
 * ia impresso no livro — mesmo quando o Google já sabia qual era o lugar.
 * Escolher da lista traz o nome oficial, a cidade, o país e o place_id.
 *
 * Digitar livremente continua permitido: se o Google estiver indisponível ou
 * o lugar não existir no índice, o formulário não pode travar.
 */
const PlaceAutocomplete = ({
  value,
  onChange,
  onSelect,
  kind = 'landmark',
  near = '',
  placeholder,
  id,
  ariaLabel,
  ariaInvalid = false,
  ariaDescribedBy,
  autoFocus = false,
  className = '',
}) => {
  const generatedId = useId();
  const inputId = id || `place-${generatedId}`;
  const listboxId = `${inputId}-listbox`;

  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [confirmedLabel, setConfirmedLabel] = useState('');

  const containerRef = useRef(null);
  // Só buscamos depois que a família digita. Sem isso, voltar ao passo com o
  // roteiro já preenchido abriria a lista sozinho sobre os campos seguintes.
  const isTyping = useRef(false);

  const closeList = useCallback(() => {
    setIsOpen(false);
    setActiveIndex(-1);
  }, []);

  useEffect(() => {
    const term = String(value || '').trim();
    if (!isTyping.current) return undefined;
    if (term.length < 3) {
      setSuggestions([]);
      closeList();
      return undefined;
    }

    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setIsLoading(true);
      try {
        const results = await fetchPlaceSuggestions(term, { kind, near, signal: controller.signal });
        setSuggestions(results);
        setIsOpen(results.length > 0);
        setActiveIndex(-1);
      } catch (error) {
        if (error.name !== 'AbortError') {
          // Silencioso de propósito: o campo segue utilizável como texto livre.
          setSuggestions([]);
          closeList();
        }
      } finally {
        setIsLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [value, kind, near, closeList]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) closeList();
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closeList]);

  const applySuggestion = (suggestion) => {
    isTyping.current = false;
    setSuggestions([]);
    setConfirmedLabel(suggestion.location_label || suggestion.name);
    onSelect?.(suggestion);
    closeList();
  };

  const handleKeyDown = (event) => {
    if (!isOpen || suggestions.length === 0) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault();
      applySuggestion(suggestions[activeIndex]);
    } else if (event.key === 'Escape') {
      closeList();
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <Input
          id={inputId}
          value={value}
          autoFocus={autoFocus}
          placeholder={placeholder}
          aria-label={ariaLabel}
          aria-invalid={ariaInvalid}
          aria-describedby={ariaDescribedBy}
          onChange={(event) => {
            isTyping.current = true;
            setConfirmedLabel('');
            onChange(event.target.value);
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
          role="combobox"
          aria-expanded={isOpen}
          aria-controls={listboxId}
          aria-autocomplete="list"
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined}
          autoComplete="off"
          className={`rounded-xl py-6 pr-10 text-base ${className}`}
        />
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
          ) : confirmedLabel ? (
            <Check className="h-4 w-4 text-secondary" aria-hidden="true" />
          ) : null}
        </span>
      </div>

      {/* Confirma o lugar reconhecido: a família vê que o nome impresso
          será o oficial, não o que ela digitou. */}
      {confirmedLabel && !isOpen && (
        <p className="mt-1 flex items-center gap-1 text-xs font-medium text-secondary">
          <MapPin className="h-3 w-3" aria-hidden="true" />
          {confirmedLabel}
        </p>
      )}

      {isOpen && suggestions.length > 0 && (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-72 w-full overflow-auto rounded-lg border border-border bg-card py-1 shadow-sm"
        >
          {suggestions.map((suggestion, index) => (
            <li
              key={suggestion.place_id}
              id={`${listboxId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
            >
              <button
                type="button"
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => applySuggestion(suggestion)}
                className={`flex w-full items-start gap-2 px-4 py-2.5 text-left transition-colors ${
                  index === activeIndex ? 'bg-primary/10' : 'hover:bg-muted/60'
                }`}
              >
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                <span className="min-w-0">
                  <span className="block truncate font-bold text-foreground">{suggestion.name}</span>
                  <span className="block truncate text-sm text-muted-foreground">
                    {suggestion.location_label || suggestion.formatted_address}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default PlaceAutocomplete;
