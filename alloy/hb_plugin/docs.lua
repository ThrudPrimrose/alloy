-- docs-md (pages.py): what an agent reading the text can use. Sphinx's navigation (toctree) goes, rST's default
-- role (`x`, a title-ref span) becomes code, a label's anchor its text, and a figure the agent cannot see becomes its caption, or nothing.
function Div(div)
  -- `.. only::` keeps text for another builder ("not html"), never the page's content
  if div.classes:includes("toctree") or div.classes:includes("only") then return {} end
end

function Span(span)
  if span.classes:includes("title-ref") then return pandoc.Code(pandoc.utils.stringify(span)) end
  if #span.classes == 0 then return span.content end  -- a label's anchor
end

function Figure(figure)
  local caption = pandoc.utils.stringify(figure.caption.long)
  if caption == "" then return {} end
  return pandoc.Para({pandoc.Emph({pandoc.Str("Figure: " .. caption)})})
end

function Image(image)
  local alt = pandoc.utils.stringify(image.caption)
  if alt == "" or alt == "image" or alt:match("^/") then return {} end
  return pandoc.Emph({pandoc.Str("Figure: " .. alt)})
end
