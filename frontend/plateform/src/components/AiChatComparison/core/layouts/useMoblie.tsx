import { useState } from 'react';

export const useMoblie = () => {
  const MminWidth = 370;
  const MmaxWidth = 790;
  //如果判断是移动端设备输出
  const [isMoblie, setIsMoblie] = useState();

  return {
    isMoblie,
    MmaxWidth,
    MminWidth,
  };
};
