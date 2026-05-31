
export const validatePhoto = (photo) => {
  if (!photo) {
    return { valid: false, error: 'Anexe uma foto da familia para gerar a capa.' };
  }
  
  const validTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
  if (!validTypes.includes(photo.type)) {
    return { valid: false, error: 'A foto precisa ser JPG, PNG ou WebP.' };
  }
  
  const maxSize = 5 * 1024 * 1024; // 5MB
  if (photo.size > maxSize) {
    return { valid: false, error: 'A foto precisa ter menos de 5MB.' };
  }
  
  return { valid: true, error: null };
};

export const validateTitle = (title) => {
  if (!title || title.trim().length === 0) {
    return { valid: false, error: 'Informe o titulo do guia.' };
  }

  return { valid: true, error: null };
};

export const validateYear = (year) => {
  const numericYear = Number(year);

  if (!Number.isInteger(numericYear) || numericYear < 2024 || numericYear > 2100) {
    return { valid: false, error: 'Informe um ano entre 2024 e 2100.' };
  }

  return { valid: true, error: null };
};

export const validateParents = (parents) => {
  if (!parents || parents.filter((parent) => parent.trim()).length === 0) {
    return { valid: false, error: 'Adicione pelo menos um responsavel.' };
  }

  const shortNames = parents.filter((parent) => parent.trim() && parent.trim().length < 2);
  if (shortNames.length > 0) {
    return { valid: false, error: 'Os nomes dos responsaveis precisam ter pelo menos 2 caracteres.' };
  }

  return { valid: true, error: null };
};

export const validateChildren = (children) => {
  if (!children || children.filter((child) => child.trim()).length === 0) {
    return { valid: false, error: 'Adicione pelo menos uma crianca.' };
  }
  
  const shortNames = children.filter((child) => child.trim() && child.trim().length < 2);
  if (shortNames.length > 0) {
    return { valid: false, error: 'Os nomes das criancas precisam ter pelo menos 2 caracteres.' };
  }
  
  return { valid: true, error: null };
};

export const validateSelectedLandmarks = (selectedLandmarks, customLandmarksText = '') => {
  if ((!selectedLandmarks || selectedLandmarks.size === 0) && !customLandmarksText.trim()) {
    return { valid: false, error: 'Selecione ou informe pelo menos um ponto turistico.' };
  }
  
  return { valid: true, error: null };
};

export const validateAllFields = (formData) => {
  const photoValidation = validatePhoto(formData.photo);
  if (!photoValidation.valid) return photoValidation;

  const titleValidation = validateTitle(formData.title);
  if (!titleValidation.valid) return titleValidation;

  const yearValidation = validateYear(formData.year);
  if (!yearValidation.valid) return yearValidation;

  const parentsValidation = validateParents(formData.parents);
  if (!parentsValidation.valid) return parentsValidation;

  const childrenValidation = validateChildren(formData.children);
  if (!childrenValidation.valid) return childrenValidation;

  const selectedLandmarksValidation = validateSelectedLandmarks(
    formData.selectedLandmarks,
    formData.customLandmarksText
  );
  if (!selectedLandmarksValidation.valid) return selectedLandmarksValidation;

  return { valid: true, error: null };
};
