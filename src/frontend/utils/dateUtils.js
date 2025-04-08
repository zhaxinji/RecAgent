/**
 * 日期工具函数库
 */

// 默认日期格式
const DEFAULT_DATE_FORMAT = 'YYYY-MM-DD';

/**
 * 格式化日期
 * @param {Date|string|number} date - 日期对象、字符串或时间戳
 * @param {string} format - 格式字符串 (YYYY=年, MM=月, DD=日, HH=时, mm=分, ss=秒)
 * @returns {string} 格式化后的日期字符串
 */
export const formatDate = (date, format = DEFAULT_DATE_FORMAT) => {
  // 如果没有提供日期，使用当前日期
  if (!date) {
    return '';
  }
  
  // 确保date是Date对象
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date;
  
  // 如果日期无效，返回空字符串
  if (isNaN(dateObj.getTime())) {
    return '';
  }
  
  // 获取日期各个部分
  const year = dateObj.getFullYear();
  const month = dateObj.getMonth() + 1;
  const day = dateObj.getDate();
  const hours = dateObj.getHours();
  const minutes = dateObj.getMinutes();
  const seconds = dateObj.getSeconds();
  
  // 格式化字符串
  return format
    .replace('YYYY', year)
    .replace('MM', padZero(month))
    .replace('DD', padZero(day))
    .replace('HH', padZero(hours))
    .replace('mm', padZero(minutes))
    .replace('ss', padZero(seconds));
};

/**
 * 将数字填充前导零
 * @param {number} num - 要填充的数字
 * @returns {string} 填充后的字符串
 */
const padZero = (num) => {
  return num.toString().padStart(2, '0');
};

/**
 * 获取相对时间描述
 * @param {Date|string|number} date - 日期对象、字符串或时间戳
 * @returns {string} 相对时间描述，如"刚刚"、"3小时前"等
 */
export const getRelativeTimeDesc = (date) => {
  if (!date) {
    return '';
  }
  
  // 确保date是Date对象
  const dateObj = typeof date === 'string' || typeof date === 'number' 
    ? new Date(date) 
    : date;
  
  // 如果日期无效，返回空字符串
  if (isNaN(dateObj.getTime())) {
    return '';
  }
  
  const now = new Date();
  const diffMs = now - dateObj;
  const diffSec = Math.floor(diffMs / 1000);
  
  // 如果是未来时间，返回具体日期
  if (diffSec < 0) {
    return formatDate(dateObj);
  }
  
  // 小于1分钟
  if (diffSec < 60) {
    return '刚刚';
  }
  
  // 小于1小时
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) {
    return `${diffMin}分钟前`;
  }
  
  // 小于1天
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) {
    return `${diffHour}小时前`;
  }
  
  // 小于1周
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) {
    return `${diffDay}天前`;
  }
  
  // 小于1个月
  if (diffDay < 30) {
    const diffWeek = Math.floor(diffDay / 7);
    return `${diffWeek}周前`;
  }
  
  // 小于1年
  const diffMonth = Math.floor(diffDay / 30);
  if (diffMonth < 12) {
    return `${diffMonth}个月前`;
  }
  
  // 大于等于1年
  const diffYear = Math.floor(diffDay / 365);
  return `${diffYear}年前`;
};

/**
 * 获取两个日期之间的天数
 * @param {Date|string|number} startDate - 开始日期
 * @param {Date|string|number} endDate - 结束日期
 * @returns {number} 天数差
 */
export const getDaysBetween = (startDate, endDate) => {
  // 确保是Date对象
  const start = typeof startDate === 'string' || typeof startDate === 'number' 
    ? new Date(startDate) 
    : startDate;
  const end = typeof endDate === 'string' || typeof endDate === 'number' 
    ? new Date(endDate) 
    : endDate;
  
  // 计算相差的毫秒数
  const diffMs = Math.abs(end - start);
  
  // 转换为天数
  return Math.floor(diffMs / (1000 * 60 * 60 * 24));
};

/**
 * 检查日期是否是同一天
 * @param {Date|string|number} date1 - 第一个日期
 * @param {Date|string|number} date2 - 第二个日期
 * @returns {boolean} 是否是同一天
 */
export const isSameDay = (date1, date2) => {
  // 确保是Date对象
  const d1 = typeof date1 === 'string' || typeof date1 === 'number' 
    ? new Date(date1) 
    : date1;
  const d2 = typeof date2 === 'string' || typeof date2 === 'number' 
    ? new Date(date2) 
    : date2;
  
  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
};

export default {
  formatDate,
  getRelativeTimeDesc,
  getDaysBetween,
  isSameDay,
}; 