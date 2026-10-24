export const getTitleNode = (text: string) => {
  return [
    {
      type: "h1",
      children: [{ text }],
      class: "cover title"
    }
  ];
};
