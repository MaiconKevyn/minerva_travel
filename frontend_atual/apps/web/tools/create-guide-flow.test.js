import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const readProjectFile = (path) => readFileSync(new URL(`../${path}`, import.meta.url), 'utf8');

test('create guide wizard asks for structured destination first and uses seven steps', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const progress = readProjectFile('src/components/GuideCreationProgress.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');

  assert.doesNotMatch(page, /Step1FamilyName/);
  assert.match(page, /case 1: return <Step3Destination \/>;/);
  assert.match(page, /case 2: return <StepTripPreferences \/>;/);
  assert.match(page, /case 3: return <Step4Attractions \/>;/);
  assert.match(page, /case 4: return <EnhancedStep5FamilyDetails \/>;/);
  assert.match(page, /case 5: return <StepActivities \/>;/);
  assert.match(page, /case 6: return <Step2CoverPhoto \/>;/);
  assert.match(page, /case 7: return <Step5Review \/>;/);
  assert.match(page, /\[1, 2, 3, 4, 5, 6, 7\]/);
  assert.match(progress, /Passo \{progressValue\} de \{visibleSteps\.length\}/);
  assert.match(progress, /role="progressbar"/);
});

test('known itinerary mode skips the preferences step and collects landmarks upfront', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const destinationStep = readProjectFile('src/components/Step3Destination.jsx');
  const attractionsStep = readProjectFile('src/components/Step4Attractions.jsx');
  const api = readProjectFile('src/utils/minerva-api.js');

  assert.match(page, /itineraryMode === 'known' \? \[1, 3, 4, 5, 6, 7\] : \[1, 2, 3, 4, 5, 6, 7\]/);
  assert.match(context, /itineraryMode === 'known' && currentStep === 1/);
  assert.match(context, /itineraryMode === 'known' && currentStep === 3/);
  assert.match(destinationStep, /Adicionar ponto tur.stico/);
  assert.match(destinationStep, /validKnownGuideDestinations/);
  assert.match(attractionsStep, /processKnownItinerary/);
  assert.match(attractionsStep, /resolveStructuredLandmarks/);
  assert.match(api, /buildStructuredLandmarksPayload/);
  assert.match(api, /api\/landmarks\/resolve-structured/);
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

test('activity selection comes after family details and before cover photo and review', () => {
  const page = readProjectFile('src/pages/CreateGuidePage.jsx');
  const activitiesStep = readProjectFile('src/components/StepActivities.jsx');
  const photoStep = readProjectFile('src/components/Step2CoverPhoto.jsx');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');
  const activityCaseIndex = page.indexOf('case 5: return <StepActivities />;');
  const photoCaseIndex = page.indexOf('case 6: return <Step2CoverPhoto />;');
  const reviewCaseIndex = page.indexOf('case 7: return <Step5Review />;');

  assert.notEqual(activityCaseIndex, -1);
  assert.notEqual(photoCaseIndex, -1);
  assert.notEqual(reviewCaseIndex, -1);
  assert.equal(activityCaseIndex < photoCaseIndex, true);
  assert.equal(photoCaseIndex < reviewCaseIndex, true);
  assert.match(activitiesStep, /Atividades da aventura/);
  assert.match(activitiesStep, /Minha melhor memória/);
  assert.match(activitiesStep, /Hora de voltar para casa/);
  assert.match(activitiesStep, /Nenhuma vem marcada automaticamente/);
  assert.match(activitiesStep, /MAX_OPTIONAL_ACTIVITIES_PER_LANDMARK/);
  assert.match(activitiesStep, /MAX_OPTIONAL_ACTIVITIES_PER_GUIDE/);
  assert.match(activitiesStep, /activity\.preview/);
  assert.match(photoStep, /foto de capa/i);
  assert.match(photoStep, /roteiro/i);
  assert.match(photoStep, /expectedCoverFamilyMemberCount/);
  assert.match(photoStep, /Quantas pessoas aparecem/);
  assert.match(context, /expectedCoverFamilyMemberCount/);
  assert.match(review, /expectedVisibleFamilyMemberCount/);
  assert.match(review, /createGuideBuilder/);
  assert.match(review, /Hora de voltar para casa/);
});

test('activity choices stay linked to point ids and are sent to the progressive builder', () => {
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');
  const api = readProjectFile('src/utils/minerva-api.js');

  assert.match(context, /landmarkActivitySelections/);
  assert.match(context, /landmark_activity_selections/);
  assert.match(context, /pruneLandmarkActivitySelections/);
  assert.match(review, /landmarkActivitySelections/);
  assert.match(review, /activityOptionForType/);
  assert.match(api, /activity_selections_json/);
  assert.match(api, /normalizeLandmarkActivitySelections/);
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

test('review step offers restaurant recommendations under the explicit no-charge contract', () => {
  const api = readProjectFile('src/utils/minerva-api.js');
  const context = readProjectFile('src/contexts/ConversationalGuideContext.jsx');
  const review = readProjectFile('src/components/Step5Review.jsx');

  assert.match(api, /RESTAURANT_RECOMMENDATIONS_EXTRA/);
  assert.match(api, /price_cents:\s*0/);
  assert.match(api, /Incluído no guia/);
  assert.match(context, /restaurantRecommendationsExtra/);
  assert.match(review, /RESTAURANT_RECOMMENDATIONS_EXTRA/);
  assert.match(review, /setRestaurantRecommendationsExtra/);
  assert.match(review, /restaurantRecommendationsExtra/);
});

test('review starts a page session without triggering legacy PDF generation', () => {
  const review = readProjectFile('src/components/Step5Review.jsx');

  assert.match(review, /Criar e revisar a capa/);
  assert.match(review, /Nenhuma imagem será gerada sem sua confirmação/);
  assert.match(review, /createGuideBuilder/);
  assert.match(review, /<GuideAssembly session=\{builderSession\}/);
  assert.doesNotMatch(review, /generatePDF|downloadGuidePdf|fetchGuidePreviewHtml|legacyGenerate/);
});

test('final assembly reviews only the cover and queues the complete guide', () => {
  const api = readProjectFile('src/utils/minerva-api.js');
  const review = readProjectFile('src/components/Step5Review.jsx');
  const assembly = readProjectFile('src/components/GuideAssembly.jsx');

  assert.match(api, /createGuideBuilder/);
  assert.match(api, /generateBuilderPageAttempt/);
  assert.match(api, /approveBuilderPage/);
  assert.match(api, /queueGuideBuilderGeneration/);
  assert.match(api, /generation-jobs/);
  assert.match(api, /getGuideJob/);
  assert.match(api, /downloadGuidePdf/);
  assert.match(api, /fetchBuilderAssetObjectUrl/);
  assert.match(api, /fetchGuideBuilderSession/);
  assert.match(api, /Idempotency-Key/);
  assert.match(review, /GuideAssembly/);
  assert.doesNotMatch(review, /legacyGenerate/);
  assert.match(assembly, /Gerar preview da capa/);
  assert.match(assembly, /Gerar nova versão/);
  assert.match(assembly, /Quer mudar alguma coisa\?/);
  assert.match(api, /revision_instruction: revisionInstruction\.trim\(\)/);
  assert.match(assembly, /MAX_COVER_ATTEMPTS/);
  assert.match(assembly, /Nova tentativa automática em/);
  assert.match(assembly, /builderGenerationRetryDelaySeconds/);
  assert.match(assembly, /isRetryableBuilderGenerationError/);
  assert.match(assembly, /Aprovar esta capa/);
  assert.match(assembly, /Criar guia completo/);
  assert.match(assembly, /Você pode fechar esta página com segurança/);
  assert.match(assembly, /Não é preciso aguardar no site/);
  assert.match(assembly, /Guia pronto e enviado/);
  assert.doesNotMatch(assembly, /GuideActivityPanel|selectedPageId|Gerar página/);
});

test('activity examples and placement APIs remain available before final cover review', () => {
  const api = readProjectFile('src/utils/minerva-api.js');
  const assembly = readProjectFile('src/components/GuideAssembly.jsx');
  const panel = readProjectFile('src/components/GuideActivityPanel.jsx');
  const activities = readProjectFile('src/utils/landmark-activities.js');

  assert.doesNotMatch(assembly, /GuideActivityPanel|handleAddActivity|handleMoveActivity/);
  assert.match(api, /addBuilderActivity/);
  assert.match(api, /moveBuilderActivity/);
  assert.match(api, /removeBuilderActivity/);
  assert.match(api, /layout_revision/);
  assert.match(panel, /Adicionar atividades/);
  assert.match(panel, /Exemplo real/);
  assert.match(panel, /Organizar páginas/);
  assert.match(panel, /draggable=/);
  assert.match(panel, /Inserir depois de/);
  assert.match(panel, /Mover .* uma posição para cima/);
  assert.match(panel, /aria-live="polite"/);
  assert.match(panel, /A imagem só será produzida/);
  assert.match(activities, /detail-hunt-real\.webp/);
  assert.match(activities, /word-search-real\.webp/);
  assert.match(activities, /painting-real\.webp/);
  assert.match(activities, /coloring-real\.webp/);
  assert.match(activities, /family-coloring-real\.webp/);
  assert.match(activities, /Família de férias para colorir/);
  assert.match(activities, /investigator-real\.webp/);
  assert.match(activities, /Investigador/);
  assert.match(activities, /Cada criança recebe uma pista/);
  assert.match(activities, /foto enviada como referência/);
});

test('signup avoids a pointless login step and never lands on an empty form', () => {
  const signup = readProjectFile('src/pages/SignupPage.jsx');
  const login = readProjectFile('src/pages/LoginPage.jsx');
  const authClient = readProjectFile('src/lib/authClient.js');

  // O cliente informa o estado da conta; a tela não inspeciona o provedor.
  assert.match(authClient, /authenticated: Boolean\(data\?\.session\)/);
  assert.match(authClient, /needsEmailConfirmation/);

  assert.match(signup, /result\.authenticated/);
  assert.match(signup, /navigate\('\/create'\)/);
  assert.match(signup, /state: \{ email, reason: 'confirm-email' \}/);
  assert.match(signup, /state: \{ email, reason: 'signed-up' \}/);
  assert.doesNotMatch(signup, /Faça login para continuar/);

  assert.match(login, /location\.state\?\.email/);
  assert.match(login, /Sua conta está pronta!/);
});

test('dashboard shows the generated cover of each guide instead of text-only cards', () => {
  const dashboard = readProjectFile('src/pages/DashboardPage.jsx');
  const cover = readProjectFile('src/components/GuideCover.jsx');
  const api = readProjectFile('src/utils/minerva-api.js');

  assert.match(dashboard, /GuideCover/);
  assert.match(dashboard, /coverUrl=\{guide\.cover_url\}/);
  assert.match(api, /fetchGuideCoverObjectUrl/);
  assert.match(api, /safeGuideCoverUrl/);
  // Capa privada: precisa de token, então nunca vai direto no src da imagem.
  assert.match(cover, /authenticatedFetch|fetchGuideCoverObjectUrl/);
  assert.match(cover, /revokeObjectURL/);
  // Guias antigos e falhas de rede caem no placeholder, sem imagem quebrada.
  assert.match(cover, /BookOpen/);
  assert.match(cover, /aspect-\[3\/4\]/);
});

test('home explains the flow and shows real product pages from our own domain', () => {
  const home = readProjectFile('src/pages/HomePage.jsx');
  const hero = readProjectFile('src/components/HomeHero.jsx');
  const howItWorks = readProjectFile('src/components/HowItWorks.jsx');
  const sampleGuide = readProjectFile('src/components/SampleGuideReader.jsx');

  assert.match(home, /HomeHero/);
  assert.match(home, /HowItWorks/);
  assert.match(home, /SampleGuideReader/);
  assert.match(howItWorks, /Aprove a sua capa/);
  assert.match(howItWorks, /Conte a viagem/);
  assert.match(howItWorks, /Receba o livro por e-mail/);
  assert.match(sampleGuide, /sample-guide\/page-/);
  assert.match(sampleGuide, /19 páginas reais/);
  assert.match(sampleGuide, /Ir para a página/);
  // O herói mostra o livro, não uma capa solta: quem chega precisa ver que há
  // atividades dentro antes de decidir criar uma conta. O leque do mockup usa
  // labirinto, diário, capa e colorir.
  assert.match(hero, /activity-examples\/cover-sample\.webp/);
  assert.match(hero, /activity-examples\/maze-real\.webp/);
  assert.match(hero, /activity-examples\/travel-diary-real\.webp/);
  assert.match(hero, /activity-examples\/coloring-real\.webp/);

  // Nenhuma imagem da vitrine pode depender de CDN de terceiros.
  for (const source of [home, hero, sampleGuide]) {
    assert.doesNotMatch(source, /horizons-cdn|https?:\/\/[^"']+\.(png|jpe?g|webp)/);
  }
});

test('home promises exactly the activity catalogue the product ships', () => {
  const showcase = readProjectFile('src/components/ActivityShowcase.jsx');
  const faq = readProjectFile('src/components/HomeFaq.jsx');

  // Uma lista escrita à mão aqui envelheceria: a home prometeria doze
  // atividades enquanto o produto já entrega dezoito.
  assert.match(showcase, /activityOptionsByCategory/);
  assert.doesNotMatch(showcase, /\b1[0-9] atividades\b/);
  assert.match(faq, /PHRASEBOOK_COUNTRIES/);
  // O preço numérico vem do backend; a home estática não pode congelá-lo.
  assert.match(faq, /compra única/i);
  assert.doesNotMatch(faq, /R\$|€\s*\d/);
  // Com a cobrança ativa, nenhuma promessa de piloto gratuito pode sobrar.
  assert.doesNotMatch(faq, /piloto/i);
});

test('the catalogue is listed once and each card says where it was assigned', () => {
  const activities = readProjectFile('src/components/StepActivities.jsx');

  // Repetir o catálogo por parada enchia a tela de cards idênticos; ele
  // aparece uma vez e o destino vira uma escolha dentro do card.
  assert.match(activities, /flex h-full flex-col/);
  assert.match(activities, /ActivityLandmarkPicker/);
  assert.match(activities, /ActivityPlanSummary/);
  assert.match(activities, /landmarksWithActivity/);
  assert.doesNotMatch(activities, /landmarks\.map\(\(landmark, landmarkIndex\)/);
  assert.doesNotMatch(activities, /Exemplo real/);
});

test('the eye opens the full page and assigning stays an explicit act', () => {
  const activities = readProjectFile('src/components/StepActivities.jsx');
  const dialog = readProjectFile('src/components/ActivityPreviewDialog.jsx');

  // Nada no card marca a atividade por acidente: o corpo é um <article> e a
  // escolha do ponto tem controle próprio.
  assert.match(activities, /Ver a página de \$\{activity\.label\} inteira/);
  assert.match(activities, /<article/);
  assert.doesNotMatch(activities, /<label/);
  assert.match(activities, /<ActivityPreviewDialog/);
  assert.match(dialog, /activityGallery/);
  assert.match(dialog, /role="tab"/);
  assert.match(dialog, /Em quais paradas esta página entra\?/);
});
