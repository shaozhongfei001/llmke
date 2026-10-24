// 富文本元素渲染统一出口

// 迁移自ChatMessage.tsx
import React from 'react';

export const renderElement = (props: any) => {
  // console.log('------------------renderElement element:', props);
  const { element, children, attributes } = props;
  switch (element.type) {
    case 'paragraph':
      return (
        <p 
          {...attributes} 
          className="mb-4 leading-7 text-gray-700 font-normal"
        >
          {children}
        </p>
      );
    case 'heading-one':
      return (
        <h1 
          {...attributes} 
          className="text-xl font-bold mb-6 text-gradient bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-cyan-500"
        >
          {children}
        </h1>
      );
    case 'heading-two':
      return (
        <h2 
          {...attributes} 
          className="text-lg font-semibold mb-4 text-gray-600 border-l-4  pl-3"
        >
          {children}
        </h2>
      );
    case 'heading-three':
      return (
        <h3 
          {...attributes} 
          className="text-lg font-medium mb-3 text-gray-600 flex items-center before:content-[''] before:w-2 before:h-2 before:rounded-full before:bg-blue-500 before:mr-2"
        >
          {children}
        </h3>
      );
    case 'bulleted-list':
      return (
        <ul 
          {...attributes} 
          className="mb-4 space-y-2 list-none pl-4"
        >
          {children}
        </ul>
      );
    case 'numbered-list':
      return (
        <ol 
          {...attributes} 
          className="mb-4 space-y-2 list-decimal pl-4 marker:text-blue-500 marker:font-medium"
        >
          {children}
        </ol>
      );
    case 'list-item':
      return (
        <li 
          {...attributes} 
          className="relative pl-6 before:absolute before:left-0 before:top-3 before:w-2 before:h-2 before:bg-blue-500 before:rounded-full before:transform before:-translate-y-1/2"
        >
          {children}
        </li>
      );
    case 'table':
      return (
        <div style={{ display: 'flex', msOverflowX:'scroll', width:"100%", maxWidth: '65vw', overflowX: 'auto', margin: '1rem 0' }}>
          <table style={{ minWidth: 380, maxwidth: '100%', borderCollapse: 'collapse', border: '1px solid #e5e7eb' }} {...attributes}>
            <tbody>{children}</tbody>
          </table>
        </div>
      );
    case 'table-row':
      return (
        <tr style={{ borderBottom: '1px solid #e5e7eb' }} {...attributes}>
          {children}
        </tr>
      );
    case 'table-cell':
      if (element.header) {
        return (
          <th
            style={{
              padding: '0.75rem 1.5rem',
              textAlign: 'left',
              fontSize: '0.875rem',
              fontWeight: 600,
              color: '#1e3a8a',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              borderRight: '1px solid #93c5fd',
              backgroundColor: '#f0f9ff'
            }}
            {...attributes}
          >
            {children}
          </th>
        );
      }
      return (
        <td
          style={{
            padding: '0.75rem 1.5rem',
            fontSize: '0.875rem',
            color: '#374151',
            borderRight: '1px solid #e5e7eb'
          }}
          {...attributes}
        >
          {children}
        </td>
      );
    case 'block-quote':
      return (
        <blockquote 
          {...attributes}
          className="border-l-4 border-blue-500 bg-blue-50 pl-4 py-2 mb-4 rounded-r-lg italic text-gray-700"
        >
          {children}
        </blockquote>
      );
    case 'code-block':
      const codeLines = element.children[0]?.text?.split('\n') || [''];
      return (

        <div {...attributes} className="mb-4 w-full rounded-lg  overflow-x-scroll bg-[#f6f8fa] border border-[#d0d7de]">
          <div className="flex w-full">
            {/* 行号区域 */}
            <div className="py-4 pr-4 pl-3 text-right select-none bg-[#f6f8fa] border-r border-[#d0d7de] text-gray-400 font-mono text-xs">
              {codeLines.map((_: string, i: number) => (
                <div key={i} className="leading-5">
                  {i + 1}
                </div>
              ))}
            </div>
            {/* 代码区域 */}
            <pre className="flex-1 p-4 m-0 overflow-x-auto bg-[#f6f8fa] text-[#1f2328]">
              <code className="font-mono text-sm leading-5">
                {children}
              </code>
            </pre>
          </div>
        </div>
      );
    case 'think':
      return (
        <div
          {...attributes}
          style={{
            background: '#f8fafc',
            borderRadius: '8px',
            border: '1px dashed #e0e7ef',
            color: '#b0b8c9',
            margin: '16px 0',
            padding: '0',
            position: 'relative',
            fontStyle: 'italic',
            overflow: 'hidden',
            display: 'flex',
          }}
          className="relative my-4"
        >
          <div style={{
            width: 4,
            background: 'linear-gradient(to bottom, #e0e7ef 60%, #f1f5f9 100%)',
            borderRadius: '2px',
            marginRight: 12,
            minHeight: '100%',
          }} />
          <div style={{ flex: 1 }}>
            <div
              style={{
                borderTop: '1px solid #e0e7ef',
                paddingTop: '8px',
                marginBottom: '6px',
                fontWeight: 500,
                color: '#a3a3a3',
                fontSize: '13px',
                letterSpacing: '1px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <span style={{ marginRight: 8, fontSize: 12 }}>💭</span>
              思考中
            </div>
            <div style={{ color: '#b0b8c9', fontSize: '13px', lineHeight: 1.7, padding: '2px 0 10px 0' }}>{children}</div>
          </div>
        </div>
      );
    // case 'retrive':
    //   return (
    //     <span
    //       {...attributes}
    //       style={{
    //         display: 'inline',
    //         alignItems: 'center',
    //         padding: '2px 3px',
    //         borderRadius: '6px',
    //         background: '#FEF3C7',
    //         color: '#B45309',
    //         border: '1px solid #FDE68A',
    //         cursor: 'pointer',
    //         margin: '0 4px',
    //         transition: 'background 0.2s',
    //         fontWeight: 600,
    //         fontSize: 10,
    //       }}
    //       title={`召回标注ID: ${element.id}`}
    //       onClick={() => {
    //         if (props.onRetriveTagClick) {
    //           props.onRetriveTagClick(element.id);
    //         }
    //       }}
    //       onMouseEnter={e => (e.currentTarget.style.background = '#FDE68A')}
    //       onMouseLeave={e => (e.currentTarget.style.background = '#FEF3C7')}
    //     >
    //       {/* <span style={{ fontWeight: 600, color: '#B45309', marginRight: 4 }}>召回标注</span>
    //       <span style={{ fontSize: 12, color: '#B45309' }}>ID: {element.id}</span> */}
    //       {children}
    //     </span>
    //   );
    default:
      return (
        <div {...attributes} className="mb-4">
          {children}
        </div>
      );
  }
};

export const renderLeaf = (props: any) => {
  const { attributes, children, leaf } = props;
  let el = children;

  // retrive-tag 行内高亮渲染
  if (leaf.retrive) {
    el = (
      <span
        {...attributes}
        style={{
          display: 'inline-block',
          background: '#e6f7ff',
          color: '#1890ff',
          border: '1px solid rgba(114,187,255,0.3)',
          borderRadius: 6,
          padding: '1px 6px',
          margin: '0 2px',
          fontWeight: 600,
          fontSize: 8,
          lineHeight: '17px',
          cursor: 'pointer',
          verticalAlign: 'middle',
        }}
        // title={leaf.id ? `召回标注ID: ${leaf.id}` : ''}
        onClick={() => {
          //console.log('老子杯垫了leaf:', leaf,attributes)
          if (props.onRetriveTagClick) {
            props.onRetriveTagClick(leaf,attributes);
          }
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#bae7ff')}
        onMouseLeave={e => (e.currentTarget.style.background = '#e6f7ff')}
      >
        {el}
      </span>
    );
    // 保证行内渲染，直接返回
    return el;
  }

  if (leaf.code) {
    el = (
      <code 
        style={{
          padding: '0.125rem 0.375rem',
          margin: '0 0.125rem',
          borderRadius: '0.25rem',
          backgroundColor: '#f6f8fa',
          color: '#1f2328',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
          fontSize: '0.875rem',
          border: '1px solid #d0d7de',
          fontWeight: leaf.bold ? 600 : 'normal',
          fontStyle: leaf.italic ? 'italic' : 'normal',
          textDecoration: [
            leaf.underline && 'underline',
            leaf.strikethrough && 'line-through'
          ].filter(Boolean).join(' ') || 'none'
        }}
      >
        {el}
      </code>
    );
  } else {
    const style: React.CSSProperties = {
      fontWeight: leaf.bold ? 600 : 'normal',
      fontStyle: leaf.italic ? 'italic' : 'normal',
      textDecoration: [
        leaf.underline && 'underline',
        leaf.strikethrough && 'line-through'
      ].filter(Boolean).join(' ') || 'none',
      color: leaf.strikethrough ? '#6b7280' : 'inherit'
    };
    el = <span style={style}>{el}</span>;
  }

  if (leaf.link) {
    el = (
      <a 
        href={leaf.link} 
        target="_blank" 
        rel="noopener noreferrer" 
        style={{
          color: '#3b82f6',
          textDecoration: 'underline'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = '#2563eb';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = '#3b82f6';
        }}
      >
        {el}
      </a>
    );
  }

  return <span {...attributes}>{el}</span>;
};
