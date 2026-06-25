import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('create guide wizard asks for structured destination first and uses six steps', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');

  assert.doesNotMatch(page, /Step1FamilyName/);
  assert.match(page, /case 1: return <Step3Destination \/>;/);
  assert.match(page, /case 2: return <StepTripPreferences \/>;/);
  assert.match(page, /case 3: return <Step4Attractions \/>;/);
  assert.match(page, /case 4: return <EnhancedStep5FamilyDetails \/>;/);
  assert.match(page, /case 5: return <Step2CoverPhoto \/>;/);
  assert.match(page, /case 6: return <Step5Review \/>;/);
  assert.match(page, /\[1, 2, 3, 4, 5, 6\]/);
  assert.match(page, /Passo \{currentStep\} de 6/);
  assert.match(context, /Math\.min\(currentStep \+ 1, 6\)/);
});

test('destination step captures repeatable structured destination fields', () => {
  const destinationStep = readProjectFile('src/components/Step3Destination.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');

  assert.match(destinationStep, /destinationsList/);
  assert.match(context, /itineraryMode/);
  assert.match(destinationStep, /Adicionar destino/);
  assert.match(destinationStep, /Pra onde voc/);
  assert.match(destinationStep, /Quando/);
  assert.match(destinationStep, /Por quantos dias/);
  assert.match(destinationStep, /known/);
  assert.match(destinationStep, /freeform/);
  assert.match(destinationStep, /suggested/);
  assert.match(destinationStep, /parseFreeformItineraryText/);
  assert.match(destinationStep, /suggestItineraryRoutes/);
  assert.match(destinationStep, /acceptSuggestedRoute/);
});

test('family details step captures the family name together with parents and children', () => {
  const details = readProjectFile('src/components/EnhancedStep5FamilyDetails.jsx');

  assert.match(details, /familyName/);
  assert.match(details, /updateFamilyName/);
  assert.match(details, /Nome da Fam.lia/);
  assert.match(details, /Crian.as/);
  assert.match(details, /Idade/);
  assert.match(details, /Respons.veis/);
});

test('cover photo step comes after route confirmation and stays before review', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const photoStep = readProjectFile('src/components/Step2CoverPhoto.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');
  const photoCaseIndex = page.indexOf('case 5: return <Step2CoverPhoto />;');
  const reviewCaseIndex = page.indexOf('case 6: return <Step5Review />;');

  assert.notEqual(photoCaseIndex, -1);
  assert.notEqual(reviewCaseIndex, -1);
  assert.equal(photoCaseIndex < reviewCaseIndex, true);
  assert.match(photoStep, /foto de capa/i);
  assert.match(photoStep, /roteiro/i);
  assert.match(photoStep, /expectedCoverFamilyMemberCount/);
  assert.match(photoStep, /Quantas pessoas aparecem/);
  assert.match(context, /expectedCoverFamilyMemberCount/);
  assert.match(review, /expectedVisibleFamilyMemberCount/);
  assert.match(review, /cover_status/);
});

test('preferences are a fixed step before attractions', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const preferences = readProjectFile('src/components/StepTripPreferences.jsx');

  assert.equal(
    page.indexOf('case 2: return <StepTripPreferences />;') <
      page.indexOf('case 3: return <Step4Attractions />;'),
    true,
  );
  assert.match(preferences, /Ritmo/);
  assert.match(preferences, /Programas que combinam/);
  assert.match(preferences, /itineraryPreferences/);
});

test('attraction selection exposes category labels filters and review context', () => {
  const api = readProjectFile('src/utils/minerva-api.js');
  const step = readProjectFile('src/components/Step4Attractions.jsx');
  const card = readProjectFile('src/components/LandmarkCard.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');

  assert.match(api, /ATTRACTION_CATEGORY_LABELS/);
  assert.match(api, /categoryLabelForAttraction/);
  assert.match(step, /activeCategory/);
  assert.match(step, /filterAttractionsByCategory/);
  assert.match(step, /Todas/);
  assert.match(card, /categoryLabelForAttraction/);
  assert.match(review, /categoryLabelForAttraction/);
});

test('review step offers restaurant recommendations as a priced optional extra', () => {
  const api = readProjectFile('src/utils/minerva-api.js');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');

  assert.match(api, /RESTAURANT_RECOMMENDATIONS_EXTRA/);
  assert.match(api, /price_cents:\s*2990/);
  assert.match(api, /R\$ 29,90/);
  assert.match(context, /restaurantRecommendationsExtra/);
  assert.match(review, /RESTAURANT_RECOMMENDATIONS_EXTRA/);
  assert.match(review, /setRestaurantRecommendationsExtra/);
  assert.match(review, /restaurantRecommendationsExtra/);
});
