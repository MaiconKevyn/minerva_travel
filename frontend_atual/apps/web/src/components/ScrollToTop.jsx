import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const ScrollToTop = () => {
  const { pathname, hash } = useLocation();

  useEffect(() => {
    // Com âncora ("/#atividades" vindo da navbar), rolar até a seção; o
    // requestAnimationFrame dá tempo de a rota nova montar o alvo.
    if (hash) {
      const frame = requestAnimationFrame(() => {
        document.querySelector(hash)?.scrollIntoView({ block: 'start' });
      });
      return () => cancelAnimationFrame(frame);
    }
    window.scrollTo(0, 0);
    return undefined;
  }, [pathname, hash]);

  return null;
};

export default ScrollToTop;
