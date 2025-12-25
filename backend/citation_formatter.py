import re
from typing import List, Optional
from backend.literature_review_generator import PaperReference

# get the last name from author string
def _get_author_last_name(author: str) -> str:
    parts = author.strip().split()
    return parts[-1] if parts else author

# format citation in APA style (Smith et al., 2023)
def format_citation_apa(paper: PaperReference) -> str:
    if not paper.authors:
        author_str = "Unknown"
    elif len(paper.authors) == 1:
        author_str = _get_author_last_name(paper.authors[0])
    elif len(paper.authors) == 2:
        author_str = f"{_get_author_last_name(paper.authors[0])} & {_get_author_last_name(paper.authors[1])}"
    else:
        author_str = f"{_get_author_last_name(paper.authors[0])} et al."

    year_str = str(paper.year) if paper.year else "n.d."
    return f"({author_str}, {year_str})"

# format citation in MLA style (Smith 42) or (Smith et al. 42)
def format_citation_mla(paper: PaperReference, page: Optional[int] = None) -> str:
    if not paper.authors:
        author_str = "Unknown"
    elif len(paper.authors) == 1:
        author_str = _get_author_last_name(paper.authors[0])
    elif len(paper.authors) == 2:
        author_str = f"{_get_author_last_name(paper.authors[0])} and {_get_author_last_name(paper.authors[1])}"
    else:
        author_str = f"{_get_author_last_name(paper.authors[0])} et al."

    if page is not None:
        return f"({author_str} {page})"
    return f"({author_str})"

# format citation in Chicago footnote style
def format_citation_chicago(paper: PaperReference, footnote_num: int = 1) -> str:
    if not paper.authors:
        author_str = "Unknown"
    elif len(paper.authors) == 1:
        author_str = paper.authors[0]
    elif len(paper.authors) == 2:
        author_str = f"{paper.authors[0]} and {paper.authors[1]}"
    elif len(paper.authors) == 3:
        author_str = f"{paper.authors[0]}, {paper.authors[1]}, and {paper.authors[2]}"
    else:
        author_str = f"{paper.authors[0]} et al."

    year_str = str(paper.year) if paper.year else "n.d."
    return f'{footnote_num}. {author_str}, "{paper.title}" ({year_str}).'

# format a single bibliography entry in APA style
def format_bibliography_entry_apa(paper: PaperReference) -> str:
    if not paper.authors:
        author_str = "Unknown."
    elif len(paper.authors) == 1:
        author_str = f"{_get_author_last_name(paper.authors[0])}, {paper.authors[0].split()[0][0]}."
    else:
        authors = []
        for i, author in enumerate(paper.authors):
            last_name = _get_author_last_name(author)
            first_initial = author.split()[0][0] if author.split() else ""
            if i == len(paper.authors) - 1 and len(paper.authors) > 1:
                authors.append(f"& {last_name}, {first_initial}.")
            else:
                authors.append(f"{last_name}, {first_initial}.")
        author_str = " ".join(authors)

    year_str = f"({paper.year})" if paper.year else "(n.d.)"
    return f"{author_str} {year_str}. {paper.title}."

# format a single bibliography entry in MLA style
def format_bibliography_entry_mla(paper: PaperReference) -> str:
    if not paper.authors:
        author_str = "Unknown."
    elif len(paper.authors) == 1:
        parts = paper.authors[0].split()
        if len(parts) >= 2:
            author_str = f"{parts[-1]}, {' '.join(parts[:-1])}."
        else:
            author_str = f"{paper.authors[0]}."
    else:
        first_author_parts = paper.authors[0].split()
        if len(first_author_parts) >= 2:
            author_str = f"{first_author_parts[-1]}, {' '.join(first_author_parts[:-1])}, et al."
        else:
            author_str = f"{paper.authors[0]}, et al."

    year_str = str(paper.year) if paper.year else "n.d."
    return f'{author_str} "{paper.title}." {year_str}.'

# format a single bibliography entry in Chicago style
def format_bibliography_entry_chicago(paper: PaperReference) -> str:
    if not paper.authors:
        author_str = "Unknown."
    elif len(paper.authors) == 1:
        parts = paper.authors[0].split()
        if len(parts) >= 2:
            author_str = f"{parts[-1]}, {' '.join(parts[:-1])}."
        else:
            author_str = f"{paper.authors[0]}."
    else:
        first_author_parts = paper.authors[0].split()
        if len(first_author_parts) >= 2:
            first_author = f"{first_author_parts[-1]}, {' '.join(first_author_parts[:-1])}"
        else:
            first_author = paper.authors[0]

        other_authors = ", ".join(paper.authors[1:-1])
        last_author = paper.authors[-1]

        if len(paper.authors) == 2:
            author_str = f"{first_author}, and {last_author}."
        else:
            author_str = f"{first_author}, {other_authors}, and {last_author}."

    year_str = str(paper.year) if paper.year else "n.d."
    return f'{author_str} "{paper.title}." {year_str}.'

# format a complete bibliography / reference list
def format_bibliography(papers: List[PaperReference], style: str = "apa") -> str:
    style = style.lower()
    entries = []

    for paper in papers:
        if style == "apa":
            entries.append(format_bibliography_entry_apa(paper))
        elif style == "mla":
            entries.append(format_bibliography_entry_mla(paper))
        elif style == "chicago":
            entries.append(format_bibliography_entry_chicago(paper))
        else:
            raise ValueError(f"Unknown citation style: {style}")

    entries.sort()
    return "\n".join(entries)

# replace numeric citations with proper formatted citations
def replace_citations_in_text(
    text: str,
    papers: List[PaperReference],
    style: str = "apa"
) -> str:
    style = style.lower()
    footnote_counter = [1]

    def replace_citation(match):
        citation_num = int(match.group(1))
        paper_idx = citation_num - 1

        if paper_idx < 0 or paper_idx >= len(papers):
            return match.group(0)

        paper = papers[paper_idx]

        if style == "apa":
            return format_citation_apa(paper)
        elif style == "mla":
            return format_citation_mla(paper)
        elif style == "chicago":
            result = format_citation_chicago(paper, footnote_counter[0])
            footnote_counter[0] += 1
            return result
        else:
            return match.group(0)

    return re.sub(r'\[(\d+)\]', replace_citation, text)