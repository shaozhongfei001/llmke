import dayjs from 'dayjs';

const useCommonCore = () => {
  const outputDateFromTimeStamp = (date: number) => {
    //格式要求：2021-06-21 08:50 。 使用DAY.JS进行处理
    return dayjs(date).format('YYYY-MM-DD HH:mm');
  };
  return {
    outputDateFromTimeStamp,
  };
};

export { useCommonCore };
