
import React from 'react';
import { motion } from 'framer-motion';
import { PlaneTakeoff } from 'lucide-react';

const DestinationGroup = ({ destination, children, index = 0 }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="mb-12 last:mb-0"
    >
      <div className="flex items-center gap-4 mb-6 pb-4 border-b border-border/50">
        <div className="w-10 h-10 rounded-full bg-secondary/10 flex items-center justify-center text-secondary shrink-0">
          <PlaneTakeoff className="w-5 h-5" />
        </div>
        <div>
          <p className="travel-label">Destino {index + 1}</p>
          <h3 className="font-display text-2xl font-bold tracking-tight text-secondary">
            {destination.country} <span className="text-muted-foreground/40 mx-2">—</span> {destination.city}
          </h3>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {children}
      </div>
    </motion.div>
  );
};

export default DestinationGroup;
