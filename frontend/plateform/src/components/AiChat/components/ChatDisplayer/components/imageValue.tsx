/** @jsxRuntime classic */
/** @jsx jsx */
import { jsx } from "@udecode/plate-test-utils";

jsx;

export const imageValue: any = ({ url }: any) => {
  return (
    <fragment>
      <himg
        align="center"
        url={
          url ||
          "https://images.unsplash.com/photo-1712688930249-98e1963af7bd?q=80&w=2070&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        }
        width="55%"
      >
        <htext />
      </himg>
    </fragment>
  );
};
