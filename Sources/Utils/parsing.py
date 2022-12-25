def extract_groups(line : str) -> list[str] :
    groups : list[str] = []
    current = ""

    block_parsing = False
    for i in range(0, len(line)) :
        if not block_parsing :

            # Start of a group
            if line[i] == "(" :
                if i == 0 :
                    block_parsing = True
                elif i != 0 and line[i - 1] != "\\" :
                    block_parsing = True
                continue

        # In that mode, we take everything that's enclosed within a group
        else :
            # End of a group
            if line[i] == ")" and line[i - 1] != "\\" :
                block_parsing = False
                groups.append(current)
                current = ""
                continue
            else :
                current += line[i]

    return groups



# Extract content from a single line of text
def parse_line(line : str) -> str :
    # We need to take out the unicode escapes if it happens to have some
    decoded_line = line.encode().decode("unicode-escape")
    tj_index = decoded_line.find("Tj")
    if tj_index == -1 :
        tj_index = decoded_line.find("TJ")

    inner_block = decoded_line

    # Looking for a very specific pattern , usually we don't have other kind of constructs
    # So that's why it's so tied to a specific implementation
    if decoded_line[0] == "[" and decoded_line[tj_index - 1] == "]":
        inner_block = decoded_line[1 : tj_index - 1]

    groups = extract_groups(inner_block)
    out = ""
    for group in groups :
        out += group

    # Removing extra escapements
    out = escape_content(out)
    return out

def escape_content(line : str) -> str :
    start = 0
    end = len(line) - 1
    index = line.find("\\", 0, end)
    escaped_version = ""
    while index != -1 :
        escaped_version += line[start : index]

        # Decode hexadecmial
        if line[index + 1] == "x" :
            pass

        # Decode octal
        if line[index + 1].isnumeric() :
            octal_str = line[index + 1 : index + 4]


        escaped_version += line[index + 1]
        start = index + 2
        index = line.find("\\", start, end)
    escaped_version += line[start : end + 1]

    return escaped_version