import re

def extractNums(processedText):    
    actNumbers = re.findall(r"№ ?[^ /,\n][^ ,\n]+", processedText)
    actNumbers = list(filter(lambda number: len(re.sub(r"[№ от]", r"", number)) > 0, actNumbers))
    return [[num] for num in actNumbers]
        
        
def extractDates(processedText):    
    datesArr = re.findall(r" «? ?\d{1,2} ?»?[^0-9/]{1,2}(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|(?:0[1-9]|1[0-2]))[^0-9/]{1,2}(?:(?:19|20)\d{2}|[89012]\d)", processedText)
    return [[date] for date in datesArr]

                
def extractOrgs(markup):  
    orgsArr = []
    personsArr = []
    for span in markup.spans:
      if span.type == "ORG" and span.stop - span.start > 5:
        org = markup.text[span.start:span.stop]
        org = org.strip()
        if (len(org.split(' ')) == 1):
          personsArr.append(org.split(' '))
        else:
          orgsArr.append(org.split(' '))

    return orgsArr, personsArr

      
def extractPersons(processedText, markup):    
    personsArr = []
    markup_persons = []

    persons = re.findall(r"(?:[A-Я][А-я]{4,} [A-Я][\.,] ?[A-Я][\.,])|(?:[A-Я][\.,] ?[A-Я][\.,] ?[A-Я][А-я]{4,})", processedText)

    for span in markup.spans:
      if span.type == "PER" and span.stop - span.start > 5:
        per = markup.text[span.start:span.stop]
        per = per.strip()
        per = re.sub(r"  +", r" ", per)
        markup_persons.append(per)

    has_changes = True
    while has_changes:
      has_changes = False
      for person in persons:
        for per in markup_persons:
          if person in per or per in persons:
            markup_persons.remove(per)
            has_changes = True
            break
                
    for person in markup_persons:     
      person = person.strip()
      person = re.sub(r"  +", r" ", person)
      personsArr.append(person.split(" "))
    
    for person in persons:     
      person = person.strip()
      person = re.sub(r"  +", r" ", person)
      personsArr.append(person.split(" "))

    return personsArr
