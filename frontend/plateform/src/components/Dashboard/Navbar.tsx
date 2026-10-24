import { Flex } from 'antd';
import { ReactNode } from 'react';
import logo from '/vite.svg';
interface NavbarType {
  children?: ReactNode;
  appName?: string;
}
function Navbar(props: NavbarType) {
  return (
    <Flex justify="space-between" align="center" className="w-full h-full">
      <Flex className="h-full" justify="start" align="center">
        <img src={logo} alt="logo" />
        <div className="h-[20px] ml-[17px] pl-[17px] border-l-[1.5px] border-r-0 border-b-0 border-t-0 border-solid border-white"></div>
        <h5 className="text-[18px] font-[400] text-white">
          {props.appName ? props.appName : 'APP名称'}
        </h5>
      </Flex>
    </Flex>
  );
}

export default Navbar;
