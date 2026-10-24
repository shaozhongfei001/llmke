export declare enum AppStatus {
    UNLOAD = 0,
    FETCHED = 1,
    LOADED = 2,
    ERROR = 3
}
export interface Annotation {
    og_size?: {
        pwidth: string;
        pheight: string;
    };
    anno_color?: string;
    pageNumber: number;
    x: number;
    y: number;
    width: number;
    height: number;
}
export interface DarwAnnotation {
    og_size?: {
        pwidth: string;
        pheight: string;
    };
    anno_color?: string;
    pageNumber: number;
    x: number;
    y: number;
    width: number;
    height: number;
}
export interface MatchAnnotation {
    anno_color?: string;
    startValue: string;
    endValue: string;
}
