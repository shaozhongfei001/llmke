// 下粗上细
const ThickThinSmallGap = () => {
  return (
    <div className="w-full">
      <div
        style={{
          borderBottom: "solid 1px red",
          width: "100%",
        }}
      ></div>
      <div
        style={{
          borderBottom: "solid 3px red",
          width: "100%",
          marginTop: 1.5,
        }}
      ></div>
    </div>
  );
};
export default ThickThinSmallGap;
