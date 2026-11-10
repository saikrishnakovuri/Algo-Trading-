import React from 'react';

const StatCard = ({ title, value, subValue, icon, color = 'cyan' }) => {
  const colorMap = {
    cyan: 'text-[#00bcd4]',
    green: 'text-[#00c853]',
    red: 'text-[#ff1744]',
    yellow: 'text-yellow-400',
  };

  return (
    <div className="bg-[#161b27] border border-[#1e2130] p-6 rounded-xl">
      <div className="flex justify-between items-start mb-4">
        <span className="text-gray-400 text-sm font-medium uppercase tracking-wider">{title}</span>
        <span className={colorMap[color]}>{icon}</span>
      </div>
      <div className="flex flex-col">
        <span className={`text-2xl font-bold font-mono ${colorMap[color]}`}>{value}</span>
        {subValue && <span className="text-gray-500 text-xs mt-1">{subValue}</span>}
      </div>
    </div>
  );
};

export default StatCard;
