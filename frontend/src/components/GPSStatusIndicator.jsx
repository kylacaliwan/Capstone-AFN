/**
 * GPS Status Indicator Component
 */
const GPSStatusIndicator = ({ status, accuracy, className = '' }) => {
  const getStatusColor = () => {
    switch (status) {
      case 'granted': return 'text-green-600';
      case 'denied': return 'text-red-600';
      case 'unknown': return 'text-yellow-600';
      default: return 'text-gray-400';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'granted': return 'GPS Active';
      case 'denied': return 'GPS Denied';
      case 'unknown': return 'GPS Unknown';
      default: return 'GPS Off';
    }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${getStatusColor().replace('text-', 'bg-')}`} />
      <span className={`text-sm font-medium ${getStatusColor()}`}>
        {getStatusText()}
      </span>
      {accuracy && (
        <span className="text-xs text-gray-500">
          ±{Math.round(accuracy)}m
        </span>
      )}
    </div>
  );
};

export default GPSStatusIndicator;