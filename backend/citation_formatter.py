from backend.literature_review_generator import PaperReference


def format_citation_apa(paper: PaperReference):
    return_str = paper.authors[0]
    if len(paper.authors) > 1:
        return_str += " et al.,"
    
    return_str += paper.year
    return "(" + return_str + ")"

def format_citation_mla(paper: PaperReference):
    return_str = paper.authors[0]
    if len(paper.authors) > 1:
        return_str += " et al.,"

    return return_str