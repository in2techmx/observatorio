import React from 'react';
import { motion } from 'framer-motion';

const Bubble = ({ region, data, isFocused }) => {
    // Random float duration to make them look organic
    const floatDuration = 3 + Math.random() * 2;
    const delay = Math.random() * 2;

    return (
        <motion.div
            className="absolute p-4 glass-panel flex flex-col items-start justify-center cursor-pointer transition-colors duration-300"
            style={{
                width: '180px',
                height: '180px',
                borderTop: `4px solid ${region.color}`,
                borderRadius: '50%',
                boxShadow: `0 0 20px ${region.color}20`, // Glow
                textAlign: 'center', // Center text for bubble shape
                alignItems: 'center', // Center flex items horizontally
                display: 'flex', // Ensure flex is explicit (it is in className but reinforcing for safety if class removed)
                padding: '1.5rem', // Ensure padding prevents text hitting edges
            }}
            animate={{
                y: [0, -15, 0],
                rotate: [0, 1, -1, 0],
                scale: isFocused ? 1.1 : 1
            }}
            transition={{
                duration: floatDuration,
                repeat: Infinity,
                ease: "easeInOut",
                delay: delay
            }}
            whileHover={{ scale: 1.15, zIndex: 50, boxShadow: `0 0 30px ${region.color}60` }}
        >
            <span className="text-xs uppercase tracking-wider opacity-70 mb-1" style={{ color: region.color }}>
                {region.name}
            </span>
            <h4 className="font-bold text-lg leading-tight mb-2 text-white">
                {data.keyword}
            </h4>
            <p className="text-xs text-gray-300 line-clamp-3">
                "{data.synthesis}"
            </p>
        </motion.div>
    );
};

export default Bubble;
