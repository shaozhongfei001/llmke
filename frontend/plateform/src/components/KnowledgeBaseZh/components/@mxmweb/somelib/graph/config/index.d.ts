export declare const nodeStyleConfig: any;
export declare const edgeStyleConfig: any;
export declare const behaviorsConfig: {
    default: (string | {
        key: string;
        type: string;
        enable: boolean;
        multiple?: undefined;
        preventDefault?: undefined;
    } | {
        key: string;
        type: string;
        multiple: boolean;
        enable?: undefined;
        preventDefault?: undefined;
    } | {
        key: string;
        type: string;
        preventDefault: boolean;
        enable?: undefined;
        multiple?: undefined;
    })[];
};
export declare const layoutConfig: any;
export declare const pluginsConfig: ({ getContextMenu, contextMenuClick, onScreenEnter, onScreenExit, }: {
    getContextMenu: (a: any, b: any) => void;
    contextMenuClick: (v: any, t: any, c: any) => void;
    onScreenEnter: () => void;
    onScreenExit: () => void;
}) => {
    default: ({
        type: string;
        key: string;
        autoFit: boolean;
        onEnter: () => void;
        onExit: () => void;
        enable?: undefined;
        offset?: undefined;
        getContent?: undefined;
        onClick?: undefined;
    } | {
        key: string;
        type: string;
        enable: (e: any) => boolean;
        offset: number[];
        getContent: (evt: any, target: any) => HTMLDivElement;
        autoFit?: undefined;
        onEnter?: undefined;
        onExit?: undefined;
        onClick?: undefined;
    } | {
        key: string;
        type: string;
        enable: boolean;
        getContent: (a: any, b: any) => void;
        onClick: (v: any, t: any, c: any) => void;
        autoFit?: undefined;
        onEnter?: undefined;
        onExit?: undefined;
        offset?: undefined;
    })[];
};
