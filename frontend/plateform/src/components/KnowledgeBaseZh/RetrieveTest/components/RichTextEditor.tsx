import { createEditor, Descendant, Element as SlateElement, BaseEditor } from 'slate';
import { Slate, Editable, withReact, RenderElementProps, RenderLeafProps, ReactEditor } from 'slate-react';
import React from 'react';

// 定义自定义文本类型
export type CustomText = {
  text: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  code?: boolean;
  retrive?: boolean;
  strikethrough?: boolean;
  link?: string;
}

// 定义基础元素类型
export interface BaseElement {
  type: string;
  children: (CustomElement | CustomText)[];
  align?: 'left' | 'center' | 'right';
}

// 定义各种元素类型
export interface ParagraphElement extends BaseElement {
  type: 'paragraph';
}

export interface HeadingOneElement extends BaseElement {
  type: 'heading-one';
}

export interface HeadingTwoElement extends BaseElement {
  type: 'heading-two';
}

export interface HeadingThreeElement extends BaseElement {
  type: 'heading-three';
}

export interface ListElement extends BaseElement {
  type: 'bulleted-list' | 'numbered-list';
}

export interface ListItemElement extends BaseElement {
  type: 'list-item';
}

export interface TableElement extends BaseElement {
  type: 'table';
}

export interface TableRowElement extends BaseElement {
  type: 'table-row';
}

export interface TableCellElement extends BaseElement {
  type: 'table-cell';
}

export interface ImageElement extends BaseElement {
  type: 'image';
  url: string;
}

export interface CodeBlockElement extends BaseElement {
  type: 'code-block';
}

export interface BlockQuoteElement extends BaseElement {
  type: 'block-quote';
}

// 组合所有元素类型
export type CustomElement =
  | ParagraphElement
  | HeadingOneElement
  | HeadingTwoElement
  | HeadingThreeElement
  | ListElement
  | ListItemElement
  | TableElement
  | TableRowElement
  | TableCellElement
  | ImageElement
  | CodeBlockElement
  | BlockQuoteElement;

declare module 'slate' {
  interface CustomTypes {
    Editor: BaseEditor & ReactEditor;
    Element: CustomElement;
    Text: CustomText;
  }
}

// ... existing code ...