export const removeNullOrUndefined = (obj: any) => {
  if (!obj || typeof obj !== "object") {
    return obj;
  }

  const result: any = {};
  for (const [key, value] of Object.entries(obj)) {
    if (value !== null && value !== undefined) {
      result[key] = value;
    }
  }
  return result;
};
