
import React from 'react';
import { Helmet } from 'react-helmet';
import { Link } from 'react-router-dom';
import { BookOpen, Camera, Heart, Sparkles, Map } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { motion } from 'framer-motion';
import Header from '@/components/Header.jsx';
import WarmCard from '@/components/WarmCard.jsx';
import { Flower, Airplane, Suitcase } from '@/components/DecorativeElements.jsx';

const HomePage = () => {
  const features = [
    {
      icon: BookOpen,
      title: 'Itinerários Personalizados',
      description: 'Crie roteiros mágicos no ritmo da sua família. Cada viagem é um novo capítulo de uma história só de vocês.',
      color: 'text-primary',
      bg: 'bg-primary/10'
    },
    {
      icon: Camera,
      title: 'Memórias Eternizadas',
      description: 'Reúna fotos e histórias em um guia que parece um livro de contos. Um tesouro para as crianças revisitarem.',
      color: 'text-secondary',
      bg: 'bg-secondary/10'
    },
    {
      icon: Heart,
      title: 'Feito com Amor',
      description: 'Sugestões de passeios que agradam todas as idades, com mapas ilustrados e dicas fáceis de seguir.',
      color: 'text-accent',
      bg: 'bg-accent/10'
    }
  ];
  
  return (
    <>
      <Helmet>
        <title>Aventuras em Família - O seu guia de viagem ilustrado</title>
        <meta name="description" content="Crie guias de viagem personalizados como livros de histórias para a sua família. Transforme cada viagem em uma aventura mágica." />
      </Helmet>
      
      <div className="min-h-screen flex flex-col">
        <Header />
        
        {/* Storybook Hero Section */}
        <section className="relative pt-12 pb-24 lg:pt-20 lg:pb-32 overflow-hidden flex-1 flex items-center">
          <Flower className="absolute top-10 right-10 w-24 h-24 text-primary opacity-20" />
          <Airplane className="absolute top-32 left-10 w-20 h-20 text-secondary opacity-20" />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.8, ease: "easeOut" }}
                className="space-y-8 text-center lg:text-left"
              >
                <div className="inline-flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm text-sm font-medium text-secondary border border-border/50">
                  <Sparkles className="w-4 h-4" />
                  Sua próxima aventura começa aqui
                </div>
                
                <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold font-serif leading-[1.1] text-foreground">
                  Crie o Guia de Viagem da <span className="text-primary relative inline-block">
                    Sua Família
                    <svg className="absolute -bottom-2 left-0 w-full" viewBox="0 0 200 12" fill="none">
                      <path d="M2 10C50 2 150 2 198 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" opacity="0.3" />
                    </svg>
                  </span>
                </h1>
                
                <p className="text-xl text-muted-foreground leading-relaxed max-w-2xl mx-auto lg:mx-0 font-medium">
                  Transforme o planejamento das férias em um divertido livro de histórias. Adicione destinos, fotos e veja a mágica acontecer.
                </p>
                
                <div className="pt-4">
                  <Button
                    asChild
                    size="lg"
                    className="rounded-full text-lg px-10 py-7 bg-primary hover:bg-primary/90 text-white shadow-[0_8px_30px_rgb(232,122,93,0.3)] hover:shadow-[0_8px_40px_rgb(232,122,93,0.4)] transition-all duration-300 hover:-translate-y-1"
                  >
                    <Link to="/create">
                      Começar Agora
                    </Link>
                  </Button>
                </div>
              </motion.div>
              
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
                className="relative"
              >
                {/* Decorative blob behind image */}
                <div className="absolute inset-0 bg-secondary/20 rounded-[100px] blur-3xl transform rotate-12 scale-110"></div>
                
                <div className="relative rounded-[40px] overflow-hidden border-8 border-white shadow-2xl transform rotate-2 hover:rotate-0 transition-transform duration-500">
                  <img
                    src="https://horizons-cdn.hostinger.com/55ef0bc5-531f-4703-88b8-d7a7a370f5db/41b7627d2fe05fb459992abfe76821db.png"
                    alt="Watercolor illustration of a happy family with backpacks and camera in front of European landmarks, surrounded by colorful flowers"
                    className="w-full h-auto object-cover aspect-[4/3]"
                  />
                  {/* Soft overlay to make it look slightly painted */}
                  <div className="absolute inset-0 bg-[#E87A5D] mix-blend-overlay opacity-20 pointer-events-none"></div>
                </div>
                
                <Suitcase className="absolute -bottom-6 -right-6 w-24 h-24 text-accent drop-shadow-lg transform -rotate-12" />
              </motion.div>
            </div>
          </div>
        </section>
        
        {/* Features Section - Zig Zag */}
        <section className="py-24 bg-white relative">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-20">
              <h2 className="text-4xl md:text-5xl font-serif font-bold mb-4">A Magia do Nosso Guia</h2>
              <p className="text-xl text-muted-foreground font-medium max-w-2xl mx-auto">
                Tudo o que você precisa para planejar e registrar as aventuras da sua família, com o encanto de um livro infantil.
              </p>
            </div>
            
            <div className="space-y-24">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className={`grid grid-cols-1 md:grid-cols-2 gap-12 md:gap-24 items-center ${
                    index % 2 === 1 ? 'md:flex-row-reverse' : ''
                  }`}
                >
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.6 }}
                    className={`${index % 2 === 1 ? 'md:order-2' : ''}`}
                  >
                    <div className={`w-20 h-20 ${feature.bg} rounded-3xl flex items-center justify-center mb-6 transform -rotate-6`}>
                      <feature.icon className={`w-10 h-10 ${feature.color}`} />
                    </div>
                    <h3 className="text-3xl md:text-4xl font-serif font-bold mb-4">{feature.title}</h3>
                    <p className="text-xl text-muted-foreground leading-relaxed font-medium">
                      {feature.description}
                    </p>
                  </motion.div>
                  
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, margin: "-100px" }}
                    transition={{ duration: 0.6 }}
                    className={`${index % 2 === 1 ? 'md:order-1' : ''}`}
                  >
                    <WarmCard className="aspect-square flex flex-col items-center justify-center text-center p-10 bg-[#FDFBF7]">
                      {index === 0 && <Map className="w-32 h-32 text-primary/40 mb-6" />}
                      {index === 1 && <Camera className="w-32 h-32 text-secondary/40 mb-6" />}
                      {index === 2 && <Heart className="w-32 h-32 text-accent/40 mb-6" />}
                      <h4 className="font-serif text-2xl font-bold opacity-80">Ilustração Mágica</h4>
                    </WarmCard>
                  </motion.div>
                </div>
              ))}
            </div>
            
            <div className="mt-32 text-center">
              <Flower className="w-16 h-16 text-primary mx-auto mb-6 opacity-80" />
              <h3 className="text-3xl font-serif font-bold mb-8">Prontos para embarcar?</h3>
              <Button
                asChild
                size="lg"
                className="rounded-full text-lg px-12 py-8 bg-secondary hover:bg-secondary/90 text-white shadow-xl hover:-translate-y-1 transition-all duration-300"
              >
                <Link to="/create">
                  Criar o Nosso Livro
                </Link>
              </Button>
            </div>
          </div>
        </section>
        
        {/* Footer */}
        <footer className="bg-muted py-12 border-t border-border mt-auto relative overflow-hidden">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml,%3Csvg viewBox=\'0 0 200 200\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noiseFilter\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.85\' numOctaves=\'3\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noiseFilter)\' opacity=\'0.02\'/%3E%3C/svg%3E')] opacity-50"></div>
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="flex flex-col md:flex-row justify-between items-center gap-6">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-white rounded-xl shadow-sm flex items-center justify-center">
                  <Heart className="w-5 h-5 text-primary" />
                </div>
                <span className="font-serif font-bold text-xl">Aventuras em Família</span>
              </div>
              <div className="flex gap-8 text-sm font-medium">
                <span className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Política de Privacidade</span>
                <span className="text-muted-foreground hover:text-foreground cursor-pointer transition-colors">Termos de Uso</span>
              </div>
              <p className="text-sm text-muted-foreground font-medium">
                © 2026 Histórias Mágicas Ltda.
              </p>
            </div>
          </div>
        </footer>
      </div>
    </>
  );
};

export default HomePage;
