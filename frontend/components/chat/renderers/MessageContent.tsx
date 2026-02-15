import React from 'react';
import CodeBlock from './CodeBlock';
import LatexRenderer from './LatexRenderer';

interface MessageContentProps {
  content: string;
}

export default function MessageContent({ content }: MessageContentProps) {
  const parseContent = () => {
    const parts: React.ReactNode[] = [];
    let currentIndex = 0;

    // Regex patterns
    const codeBlockPattern = /```(\w+)?\n([\s\S]*?)```/g;
    const inlineCodePattern = /`([^`]+)`/g;
    const blockLatexPattern = /\$\$([\s\S]*?)\$\$/g;
    const inlineLatexPattern = /\$([^\$]+)\$/g;

    // Find all matches for code blocks
    const matches: Array<{ type: string; start: number; end: number; content: string; language?: string }> = [];

    let match;
    
    // Code blocks
    while ((match = codeBlockPattern.exec(content)) !== null) {
      matches.push({
        type: 'code-block',
        start: match.index,
        end: match.index + match[0].length,
        content: match[2],
        language: match[1] || 'python'
      });
    }
    
    // Block LaTeX
    codeBlockPattern.lastIndex = 0;
    while ((match = blockLatexPattern.exec(content)) !== null) {
      matches.push({
        type: 'latex-block',
        start: match.index,
        end: match.index + match[0].length,
        content: match[1]
      });
    }

    // Sort matches by position
    matches.sort((a, b) => a.start - b.start);

    // Build parts array
    matches.forEach((m, index) => {
      // Add text before this match
      if (m.start > currentIndex) {
        const textBefore = content.slice(currentIndex, m.start);
        parts.push(<span key={`text-before-${index}`}>{parseInlineFormatting(textBefore, parts.length)}</span>);
      }

      // Add the match
      if (m.type === 'code-block') {
        parts.push(
          <CodeBlock key={`code-${index}`} code={m.content} language={m.language || 'python'} />
        );
      } else if (m.type === 'latex-block') {
        parts.push(
          <LatexRenderer key={`latex-${index}`} content={m.content} isBlock />
        );
      }

      currentIndex = m.end;
    });

    // Add remaining text
    if (currentIndex < content.length) {
      const remainingText = content.slice(currentIndex);
      parts.push(<span key="text-remaining">{parseInlineFormatting(remainingText, parts.length)}</span>);
    }

    return parts.length > 0 ? parts : content;
  };

  const parseInlineFormatting = (text: string, baseKey: number) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Parse markdown headers first
    const lines = text.split('\n');
    const processedLines: React.ReactNode[] = [];
    
    lines.forEach((line, lineIndex) => {
      // Check for headers
      if (line.startsWith('### ')) {
        processedLines.push(
          <h3 key={`h3-${baseKey}-${lineIndex}`} className="text-sm font-bold text-slate-800 mt-3 mb-2">
            {line.substring(4)}
          </h3>
        );
      } else if (line.startsWith('## ')) {
        processedLines.push(
          <h2 key={`h2-${baseKey}-${lineIndex}`} className="text-base font-bold text-slate-800 mt-4 mb-2">
            {line.substring(3)}
          </h2>
        );
      } else if (line.startsWith('# ')) {
        processedLines.push(
          <h1 key={`h1-${baseKey}-${lineIndex}`} className="text-lg font-bold text-slate-800 mt-4 mb-2">
            {line.substring(2)}
          </h1>
        );
      } else if (line.startsWith('* ') || line.startsWith('- ')) {
        // Bullet list item
        processedLines.push(
          <div key={`li-${baseKey}-${lineIndex}`} className="flex gap-2 my-1">
            <span className="text-slate-600">•</span>
            <span className="flex-1">{parseInlineCode(line.substring(2), `${baseKey}-${lineIndex}`)}</span>
          </div>
        );
      } else if (/^\d+\.\s/.test(line)) {
        // Numbered list item
        const match = line.match(/^(\d+)\.\s(.+)$/);
        if (match) {
          processedLines.push(
            <div key={`oli-${baseKey}-${lineIndex}`} className="flex gap-2 my-1">
              <span className="text-slate-600 font-medium">{match[1]}.</span>
              <span className="flex-1">{parseInlineCode(match[2], `${baseKey}-${lineIndex}`)}</span>
            </div>
          );
        }
      } else if (line.trim()) {
        // Regular line - parse inline code and formatting
        processedLines.push(
          <span key={`line-${baseKey}-${lineIndex}`}>
            {parseInlineCode(line, `${baseKey}-${lineIndex}`)}
            {lineIndex < lines.length - 1 && <br />}
          </span>
        );
      } else {
        processedLines.push(<br key={`br-${baseKey}-${lineIndex}`} />);
      }
    });

    return <>{processedLines}</>;
  };

  const parseInlineCode = (text: string, key: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Inline code
    const inlineCodePattern = /`([^`]+)`/g;
    let match;
    
    while ((match = inlineCodePattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const textPart = text.slice(lastIndex, match.index);
        parts.push(<span key={`${key}-text-${parts.length}`}>{parseBoldItalic(textPart, `${key}-${parts.length}`)}</span>);
      }
      
      parts.push(
        <code 
          key={`${key}-code-${parts.length}`}
          className="px-1.5 py-0.5 bg-slate-100 text-slate-800 rounded text-sm font-mono"
        >
          {match[1]}
        </code>
      );
      
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(<span key={`${key}-end-${parts.length}`}>{parseBoldItalic(text.slice(lastIndex), `${key}-${parts.length}`)}</span>);
    }

    return parts.length > 0 ? <>{parts}</> : text;
  };

  const parseBoldItalic = (text: string, key: string) => {
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;

    // Bold pattern: **text**
    const boldPattern = /\*\*([^*]+)\*\*/g;
    let match;
    
    while ((match = boldPattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const textPart = text.slice(lastIndex, match.index);
        parts.push(<span key={`${key}-text-${parts.length}`}>{parseInlineLatex(textPart, `${key}-${parts.length}`)}</span>);
      }
      
      parts.push(
        <strong key={`${key}-bold-${parts.length}`} className="font-bold">
          {match[1]}
        </strong>
      );
      
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(<span key={`${key}-end-${parts.length}`}>{parseInlineLatex(text.slice(lastIndex), `${key}-${parts.length}`)}</span>);
    }

    return parts.length > 0 ? <>{parts}</> : parseInlineLatex(text, key);
  };

  const parseInlineLatex = (text: string, key: string) => {
    const inlineLatexPattern = /\$([^\$]+)\$/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = inlineLatexPattern.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(<span key={`${key}-text-${parts.length}`}>{text.slice(lastIndex, match.index)}</span>);
      }
      
      parts.push(
        <LatexRenderer key={`${key}-latex-${parts.length}`} content={match[1]} />
      );
      
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(<span key={`${key}-end`}>{text.slice(lastIndex)}</span>);
    }

    return parts.length > 0 ? <>{parts}</> : text;
  };

  return <div className="leading-relaxed">{parseContent()}</div>;
}
