export const PixelLogo = ({ className = "w-8 h-8" }: { className?: string }) => {
  return (
    <svg 
      viewBox="0 0 10 10" 
      className={className} 
      fill="currentColor" 
      xmlns="http://www.w3.org/2000/svg"
      style={{ imageRendering: 'pixelated' }}
    >
      {/* Cat Pixel Art */}
      {/* Ears */}
      <rect x="1" y="0" width="2" height="2" />
      <rect x="7" y="0" width="2" height="2" />
      
      {/* Head Top */}
      <rect x="2" y="1" width="6" height="1" />
      
      {/* Main Face */}
      <rect x="1" y="2" width="8" height="6" />
      
      {/* Eyes (White) */}
      <rect x="2" y="4" width="2" height="2" fill="white" />
      <rect x="6" y="4" width="2" height="2" fill="white" />
      
      {/* Pupils (Black/Inner) */}
      <rect x="3" y="5" width="1" height="1" fill="black" />
      <rect x="7" y="5" width="1" height="1" fill="black" />
      
      {/* Nose (Pink) */}
      <rect x="4" y="6" width="2" height="1" fill="#FFB6C1" />
      
      {/* Whiskers (Optional/Darker accent) */}
      <rect x="0" y="5" width="1" height="1" opacity="0.5" />
      <rect x="9" y="5" width="1" height="1" opacity="0.5" />
      
      {/* Chin */}
      <rect x="3" y="8" width="4" height="1" />
    </svg>
  )
}
