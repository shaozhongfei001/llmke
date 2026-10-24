export declare const mockData: {
    edges: {
        id: string;
        type: string;
        source: string;
        target: string;
        properties: {
            src_id: string;
            cust_no: string;
            acct_no: string;
            weight: number;
            dst_id: string;
        };
        directed: boolean;
    }[];
    nodes: ({
        id: string;
        data: {
            name: string;
        };
        properties?: undefined;
        primaryKey?: undefined;
    } | {
        id: string;
        properties: {
            cert_type: string;
            cert_no: string;
            cust_type: string;
            cust_no: string;
            cust_name: string;
        };
        primaryKey: string;
        data: {
            name: string;
        };
    } | {
        id: string;
        properties: {
            cert_type: string;
            cert_no: string;
            cust_type: string;
            cust_no: string;
            cust_name: string;
        };
        primaryKey: string;
        data?: undefined;
    })[];
};
export declare const mockData2: {
    nodes: {
        id: string;
        data: {
            name: string;
        };
    }[];
};
