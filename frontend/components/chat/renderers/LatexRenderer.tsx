import React from 'react';
import 'katex/dist/katex.min.css';
import { InlineMath, BlockMath } from 'react-katex';

interface LatexRendererProps {
  content: string;
  isBlock?: boolean;
}

export default function LatexRenderer({ content, isBlock = false }: LatexRendererProps) {
  try {
    if (isBlock) {
      return (
        <div className="my-4 overflow-x-auto">
          <BlockMath math={content} />
        </div>
      );
    } else {
      return <InlineMath math={content} />;
    }
  } catch (error) {
    console.error('LaTeX rendering error:', error);
    return <code className="text-rose-600 bg-rose-50 px-1 rounded">{content}</code>;
  }
}
