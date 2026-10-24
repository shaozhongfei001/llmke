import React from 'react';
import { Button } from 'antd';
import { useNavigate } from 'react-router-dom';

export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-[#141414] flex items-center justify-center p-4">
      <div className="text-center">
        {/* 动画容器 */}
        <div className="relative w-[300px] h-[300px] md:w-[400px] md:h-[400px] mx-auto mb-8">
          {/* 背景星星 */}
          <div className="absolute inset-0">
            <div className="stars"></div>
            <div className="stars2"></div>
            <div className="stars3"></div>
          </div>
          
          {/* 404文字 */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-8xl font-bold text-white opacity-20 animate-pulse">
              404
            </div>
          </div>

        </div>

        <h2 className="text-2xl md:text-3xl font-bold text-white mb-4">
          哎呀！看来你迷失在太空了
        </h2>
        <p className="text-blue-200 mb-8">
          别担心，让我们一起回到地球吧
        </p>
        <Button 
          type="primary"
          onClick={() => navigate('/')}
          className="hover:opacity-90"
        >
          返回首页
        </Button>
      </div>

      <style>{`
        @keyframes twinkle {
          0%, 100% { opacity: 0; }
          50% { opacity: 1; }
        }

        @keyframes float {
          0%, 100% { transform: translate(-50%, -50%) translateY(-10px); }
          50% { transform: translate(-50%, -50%) translateY(10px); }
        }

        @keyframes wobble {
          0%, 100% { transform: rotate(-5deg); }
          50% { transform: rotate(5deg); }
        }

        @keyframes planet-texture {
          0% { background-position: 0% 0%; }
          100% { background-position: 200% 0%; }
        }

        .stars, .stars2, .stars3 {
          position: absolute;
          inset: 0;
          background: transparent;
          background-image: radial-gradient(white 1px, transparent 1px);
          animation: twinkle 2s infinite;
        }

        .stars { background-size: 50px 50px; }
        .stars2 { 
          background-size: 30px 30px;
          animation-delay: 0.5s;
        }
        .stars3 { 
          background-size: 20px 20px;
          animation-delay: 1s;
        }

        .animate-spin-slow {
          animation: spin 20s linear infinite;
        }

        .animate-float {
          animation: float 4s ease-in-out infinite;
        }

        .animate-astronaut-wobble {
          animation: wobble 4s ease-in-out infinite;
        }

        .animate-planet-texture {
          animation: planet-texture 20s linear infinite;
        }
      `}</style>
    </div>
  );
} 