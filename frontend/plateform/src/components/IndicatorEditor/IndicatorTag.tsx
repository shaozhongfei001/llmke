import "./indicatorTag.css";

const IndicatorTag = (props) => {
  const { title, ...rest } = props;
  console.log("IndicatorTag props:", props);
  return (
    <span
      {...rest}
      contentEditable={false}
      data-indicator-tag="true"
      className="indicator-tag"
    >
      {title}
    </span>
  );
};

export default IndicatorTag;
