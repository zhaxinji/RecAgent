import { useState, useEffect } from 'react';

/**
 * 防抖钩子函数
 * 
 * @param {any} value - 需要防抖的值
 * @param {number} delay - 防抖延迟时间(毫秒)
 * @returns {any} - 防抖后的值
 */
export function useDebounce(value, delay) {
  // 存储防抖后的值
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    // 设置计时器在指定延迟后更新防抖值
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    // 在下一次effect运行前清除计时器
    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]); // 当value或delay改变时重新运行effect

  return debouncedValue;
} 