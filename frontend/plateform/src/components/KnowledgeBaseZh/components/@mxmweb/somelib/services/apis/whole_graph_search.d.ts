export interface WholeGraphSearchRequest {
    limit?: number;
    spaceName: string;
    fileId?: string;
}
export interface WholeGraphSearchResponse {
    data: any;
    success: boolean;
    message?: string;
}
export declare const wholeGraphSearchConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const getWholeGraphStatisticsConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const getNodeInfoConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const getEdgeInfoConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const nodeSearchConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const edgeSearchConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const cypherSearchConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare const nodeStepSearchConfig: {
    url: string;
    method: string;
    mockData: {
        data: {};
        success: boolean;
    };
    description: string;
    request_type: WholeGraphSearchRequest;
    response_type: WholeGraphSearchResponse;
};
export declare function wholeGraphSearch(network: {
    baseURL: string;
    token?: string;
}, data: WholeGraphSearchRequest): Promise<WholeGraphSearchResponse>;
export declare function getWholeGraphStatistics(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function getNodeInfo(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function getEdgeInfo(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function nodeSearch(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function edgeSearch(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function cypherSearch(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
export declare function nodeStepSearch(network: {
    baseURL: string;
    token?: string;
}, data: any): Promise<any>;
