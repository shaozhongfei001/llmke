type Iprops = {
  children: JSX.Element;
  open: boolean;
};
const OutlineExtractResLayout: React.FC<Iprops> = ({
  children,
  open
}: Iprops) => {
  return (
    <div
      className="fixed left-0 top-[60px] w-[100vw] h-[calc(100vh-60px)] bg-white z-[99] overflow-hidden"
      style={{
        display: open ? "block" : "none",
        opacity: open ? 1 : 0
      }}
    >
      {children}
    </div>
  );
};
export default OutlineExtractResLayout;
