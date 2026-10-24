import { INDICATOR_TAG } from "./elemntAndLeafType";
import IndicatorTag from "./IndicatorTag";

export const renderElementCb = ({ attributes, children, element }: any) => {
  switch (element.type) {
    case INDICATOR_TAG:
      const { ref, ...rest } = attributes;
      return (
        <IndicatorTag asChild title={element.title} ref={ref} {...rest}>
          {children}
        </IndicatorTag>
      );
    default:
      return (
        <p {...attributes} className="m-0">
          {children}
        </p>
      );
  }
};

export const LeafCb = ({ attributes, children, leaf }: any) => {
  if (leaf[INDICATOR_TAG]) {
    return (
      <IndicatorTag title={leaf.title} {...attributes}>
        {children}
      </IndicatorTag>
    );
  }
  return <span {...attributes}>{children}</span>;
};
