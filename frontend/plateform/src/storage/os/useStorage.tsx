import { useEffect, useMemo, useState } from 'react';
import { InitiaSaiclStore } from './config';

export type SaiclStoreProps = typeof InitiaSaiclStore;

type UpdateValue<T> = (key: string, newValue: T) => void;
type ClearValue = (key: string) => void;
type StorageType = 'local' | 'session';

interface StorageResult<T> {
  value: T;
  update: UpdateValue<T>;
  remove: ClearValue;
  get: (keys: string | string[]) => any;
  add: (data: Record<string, any>) => void;
  clear: () => string;
  isUserLoggedIn: boolean;
}

interface StorageOptions<T> {
  storeName: string;
  initialValue?: T;
  storageType?: StorageType;
}
function useStorage<T>(options: StorageOptions<T>): StorageResult<T> {
  const { storeName, initialValue = InitiaSaiclStore as unknown as T, storageType = 'local' } = options;
  const storage = storageType === 'local' ? localStorage : sessionStorage;

  const [value, setValue] = useState<T>(() => {
    const storedValue = storage.getItem(storeName);
    return storedValue !== null ? JSON.parse(storedValue) : initialValue;
  });

  const update: UpdateValue<T> = (key, newValue) => {
    const updatedValue = { ...value, [key]: newValue };
    setValue(updatedValue);
    storage.setItem(storeName, JSON.stringify(updatedValue));
  };

  const remove: ClearValue = (key) => {
    const updatedValue = { ...(value as Record<string, unknown>) };
    delete updatedValue[key];
    setValue(updatedValue as T);
    storage.setItem(storeName, JSON.stringify(updatedValue));
  };

  const get = (keys: string | string[]) => {
    const storedValue = storage.getItem(storeName);
    const parsedValue = storedValue !== null ? JSON.parse(storedValue) : null;
    if (typeof keys === 'string') {
      return parsedValue !== null && parsedValue.hasOwnProperty(keys)
        ? parsedValue[keys]
        : null;
    } else {
      return keys.map((key) =>
        parsedValue !== null && parsedValue.hasOwnProperty(key) ? parsedValue[key] : null
      );
    }
  };

  const add = (data: Record<string, any>) => {
    const storedValue = storage.getItem(storeName);
    const parsedValue = storedValue !== null ? JSON.parse(storedValue) : {};
    const updatedValue = { ...parsedValue, ...data };

    setValue(updatedValue);
    storage.setItem(storeName, JSON.stringify(updatedValue));
  };

  const clear = () => {
    try {
      const emptyValue = initialValue !== undefined ? initialValue : ({} as SaiclStoreProps);
      setValue(emptyValue as any);
      storage.setItem(storeName, JSON.stringify(emptyValue));
      return '存储已清空';
    } catch (e) {
      return '存储清空失败';
    }
  };

  const calculateIsUserLoggedIn = () => {
    const storedValue = storage.getItem(storeName);
    const parsedValue = storedValue !== null ? JSON.parse(storedValue) : null;

    if (parsedValue && parsedValue.userInfo && Object.keys(parsedValue.userInfo).length > 0) {
        return true;
    }
    return false;
};

  const [isUserLoggedIn, setIsUserLoggedIn] = useState<boolean>(calculateIsUserLoggedIn());

  useEffect(() => {
    setIsUserLoggedIn(calculateIsUserLoggedIn());
  }, [value]);

  return { value, update, remove, get, add, clear, isUserLoggedIn };
}

export default useStorage;