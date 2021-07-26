#!/usr/bin/env python
# coding: utf-8

# In[1]:


import os
import re
import random   
import io
import time
from shutil import move

import pdfminer
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams

from pdf2image import convert_from_path
from PIL import Image, ImageDraw, ImageFont

from navec import Navec
from slovnet import NER
from ipymarkup import show_span_ascii_markup as show_markup


# In[2]:


def get_files(dirpath, ext):
    files = [s for s in os.listdir(dirpath)
         if os.path.isfile(os.path.join(dirpath, s)) and os.path.splitext(s)[1] == ext]
    files.sort()
    return files


def createDir(dirpath, ext):
    if os.path.exists(dirpath):
        for file in get_files(dirpath, ext):
            os.remove(os.path.join(dirpath, file))
    else:
        os.mkdir(dirpath)
        
def createDirIfNotExist(dirpath):
    if not os.path.exists(dirpath):
        os.mkdir(dirpath)


# In[3]:


def draw_words(first_line_index, last_line_index, words, text_lines,
                drawn_boxes, xmls_boxes, pageNum, field_type, border_color):
    
        
    if first_line_index == last_line_index:
        
        first_line = text_lines[first_line_index]
        chars = []
        for elem in first_line._objs:
            if isinstance(elem, pdfminer.layout.LTChar):
                chars.append(elem)        
        first_line._objs = chars
        first_line_text = first_line.get_text()

        x_left = first_line_text.index(words[0])
        offset = x_left
        for word in words[:len(words)-1]:
            offset += len(word)

        if len(words) == 1:
            x_right = x_left + len(words[0]) - 1
        else:
            x_right = first_line_text.find(words[len(words) - 1], offset) + len(words[len(words) - 1]) - 1
        
        if x_right == -1:
            return False
        
        return drawElement(
                first_line._objs[x_left].bbox[0] - 2, 
                first_line._objs[x_left].bbox[1] - 3,
                first_line._objs[x_right].bbox[2] + 2,
                first_line._objs[x_right].bbox[3] + 3,
                ' '.join(words),
                drawn_boxes, xmls_boxes, pageNum,
                field_type=field_type, border_color=border_color)
    else:
        
        first_line = text_lines[first_line_index]
        chars = []
        for elem in first_line._objs:
            if isinstance(elem, pdfminer.layout.LTChar):
                chars.append(elem)        
        first_line._objs = chars
        first_line_text = first_line.get_text()

        x_left = first_line_text.index(words[0])

        if drawElement(
                first_line._objs[x_left].bbox[0] - 2, 
                first_line._objs[x_left].bbox[1] - 3,
                first_line._objs[len(first_line._objs) - 1].bbox[2] + 2,
                first_line._objs[len(first_line._objs) - 1].bbox[3] + 3,
                ' '.join(words),
                drawn_boxes, xmls_boxes, pageNum,
                field_type=field_type, border_color=border_color):
            
            last_line = text_lines[last_line_index]
            chars = []
            for elem in last_line._objs:
                if isinstance(elem, pdfminer.layout.LTChar):
                    chars.append(elem)        
            last_line._objs = chars
            last_line_text = last_line.get_text()

            x_right = last_line_text.index(words[len(words) - 1]) + len(words[len(words) - 1]) - 1

            drawElement(
                    last_line._objs[0].bbox[0] - 2, 
                    last_line._objs[0].bbox[1] - 3,
                    last_line._objs[x_right].bbox[2] + 2,
                    last_line._objs[x_right].bbox[3] + 3,
                    ' '.join(words),
                    drawn_boxes, xmls_boxes, pageNum,
                    field_type=field_type, border_color=border_color)
            
            for middle_line_index in range(first_line_index + 1, last_line_index):
                middle_line = text_lines[middle_line_index]
                chars = []
                for elem in middle_line._objs:
                    if isinstance(elem, pdfminer.layout.LTChar):
                        chars.append(elem)        
                middle_line._objs = chars
                middle_line_text = middle_line.get_text()

                drawElement(
                        middle_line._objs[0].bbox[0] - 2, 
                        middle_line._objs[0].bbox[1] - 3,
                        middle_line._objs[len(middle_line._objs) - 1].bbox[2] + 2,
                        middle_line._objs[len(middle_line._objs) - 1].bbox[3] + 3,
                        ' '.join(words),
                        drawn_boxes, xmls_boxes, pageNum,
                        field_type=field_type, border_color=border_color)

            return True
        
        return False
    


# In[4]:


def highLightWords(words, text_lines, drawn_boxes, xmls_boxes, pageNum,
                   field_type=None, border_color="green", after_word=None):
    
    after_word_found = True if after_word is None else False
    
    for first_line_index in range(len(text_lines)):
        
        first_line = text_lines[first_line_index]
        
        chars = []
        for elem in first_line._objs:
            if isinstance(elem, pdfminer.layout.LTChar):
                chars.append(elem)        
                
        first_line._objs = chars
        first_line_text = first_line.get_text()
        
        founded_words = []
        
        if not after_word_found:
            if after_word not in first_line_text:
                continue
            else:
                after_word_found = True

        if words[0] not in first_line_text:
            continue

        added_new_word = True
        line_index = first_line_index
        
        while added_new_word:
            added_new_word = False
            
            if line_index == len(text_lines):
                return False
            
            line = text_lines[line_index]
        
            chars = []
            for elem in line._objs:
                if isinstance(elem, pdfminer.layout.LTChar):
                    chars.append(elem)        
                    
            line._objs = chars
            line_text = line.get_text()
            
            position = 0
            for word in words[len(founded_words):]:
                if word in line_text:
                    position = line_text.find(word, position)
                    if position != -1:
                        founded_words.append(word)
                        added_new_word = True
                    else:
                        break
                else:
                    break
                    
            if len(words) == len(founded_words):
                if draw_words(first_line_index, line_index, 
                            words, text_lines,
                            drawn_boxes, xmls_boxes, pageNum,
                            field_type=field_type, border_color=border_color) == True:
                    return True
                else:
                    break
                
            line_index += 1
    return False


# In[5]:


def drawElement(x0, y0, x1, y1, text_value, drawn_boxes, xmls_boxes, pageNum,
                field_type=None, border_color="green"):

    bbox = (int(DPI_SCALE * x0 - 5), int(DPI_SCALE * y0 - 5) - 10000 * pageNum,
                int(DPI_SCALE * x1 + 5), int(DPI_SCALE * y1 + 5) - 10000 * pageNum)

    if not (bbox, text_value) in drawn_boxes:
        drawn_boxes.append([bbox, text_value])
        if field_type is not None:
            xmls_boxes.append({'field_type': field_type, 'text_value': text_value, 
                               'bbox': bbox, "pageNum": pageNum, "border_color": border_color})
        return True

    return False


def parse_obj(lt_objs, text_lines_to_handle):
    global rawText
    
#     sorted_objs = list(filter(
#         lambda obj: isinstance(obj, pdfminer.layout.LTTextBoxHorizontal), lt_objs))
    
#     sorted_objs = sorted(sorted_objs, 
#                          key = lambda obj: (int((int(obj.y0) + int(obj.y1)) / 2), -obj.x0), reverse=True)
    
    for text_box in lt_objs:
        if isinstance(text_box, pdfminer.layout.LTTextBoxHorizontal):
            for line in sorted(text_box._objs, key=lambda obj: obj.y1, reverse=True):
                text = line.get_text()
                if len(text) > 5:
                    text_lines_to_handle.append(line)
                    rawText += text[:-1]
                    if text[-1:] == "\n":
                        rawText += " "  
                    else:
                        if text[-1:] == " ":
                            rawText += " "  
                        else:
                            rawText += text[-1:] + " "  


# # Markup docs

# In[6]:


def highLightNums(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nAct number:")
    actNumbers = re.findall(r"№ ?[^ /,\n][^ ,\n]+", processedText)
    for actNum in actNumbers:
        print("-", actNum)
        highLightWords([actNum], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="Number", border_color=ACT_NUM_CLR)
        
        
def highLightDates(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nDates:")
    datesArr = re.findall(r" «? ?\d{1,2} ?»?[^0-9/]{1,2}(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря|(?:0[1-9]|1[0-2]))[^0-9/]{1,2}(?:(?:19|20)\d{2}|[89012]\d)", processedText)
    for date in datesArr:
        date = date.strip()
        print("-", date)
        highLightWords([date], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="Date", border_color=DATE_CLR)

        
def highLightAddresses(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nAddresses:")
    for i in range(len(text_lines) - 1):
        textBox = text_lines[i]
        text = textBox.get_text()
        address1 = addr_extractor.find(text)
        if address1 is not None:
            address1words = []
            parts = address1.fact.parts

            for part in parts:
                if part.value is not None:
                    address1words.append(part.value)

            if len(address1words) == 0:
                continue

            if len(address1words) == 1 and parts[0].type != "город":
                continue

            textBoxNext = text_lines[i+1]
            textNext = textBoxNext.get_text()
            address2 = addr_extractor.find(text + " " + textNext)
            if address2 is not None:
                address2words = []
                parts = address2.fact.parts

                for part in parts:
                    if part.value is not None:
                        address2words.append(part.value)

                print("-", ' '.join(address2words))
                highLightWords(address2words, text_lines, drawnBoxes, xmlsBoxes, pageNum,
                               field_type="ADDRESS", border_color=ADDR_CLR)

                
def highLightOrgs(markup, text_lines, drawnBoxes, xmlsBoxes, pageNum):  
    print("\nOrgs:")
    for span in markup.spans:
        if span.type == "ORG" and span.stop - span.start > 5:
            org = markup.text[span.start:span.stop]
            org = org.strip()
            
            print("-", org)
            if len(org.split(" ")) == 1:
                highLightWords(org.split(" "), text_lines, drawnBoxes, xmlsBoxes, pageNum,
                           field_type="Person", border_color=PER_CLR)

            highLightWords(org.split(" "), text_lines, drawnBoxes, xmlsBoxes, pageNum,
                           field_type="Org", border_color=ORG_CLR)

            
def highLightPersons(processedText, markup, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nPersons:")
    markup_persons = []
    for span in markup.spans:
        if span.type == "PER" and span.stop - span.start > 5:
            per = markup.text[span.start:span.stop]
            per = per.strip()
            per = re.sub(r"  +", r" ", per)
#             print("-", per)
#             if len(per.split(" ")) <= 1:
#                 continue
            markup_persons.append(per)
#             highLightWords(per.split(" "), text_lines, drawnBoxes, xmlsBoxes, pageNum,
#                            field_type="Person", border_color=PER_CLR)

#     persons = re.findall(r"(?:[A-Я][А-я]+ [A-Я|а-я]\. ?[A-Я|а-я]\.)|(?:[A-Я|а-я]\. ?[A-Я|а-я]\. ?[A-Я][А-я]+)", processedText)
    persons = re.findall(r"(?:[A-Я][А-я]{4,} [A-Я|а-я][\.,] ?[A-Я|а-я][\.,])|(?:[A-Я|а-я][\.,] ?[A-Я|а-я][\.,] ?[A-Я][А-я]{4,})", processedText)

    has_changes = True
    while has_changes:
        has_changes = False
        for person in persons:
            for per in markup_persons:
                if person in per or per in persons:
                    markup_persons.remove(per)
                    has_changes = True
                    break
                
    for per in markup_persons:     
        per = per.strip()
        per = re.sub(r"  +", r" ", per)
        print("-", per)
        highLightWords(per.split(" "), text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="Person", border_color=PER_CLR)
        
    print("\nPersons regex XXXX X.X. | X.X. XXXX:")
    
    for person in persons:     
        person = person.strip()
        person = re.sub(r"  +", r" ", person)
        print("-", person)
        highLightWords(person.split(" "), text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="Person", border_color=PER_CLR)
    
    
def highLightMoney(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nMoney:")
    moneyArr = re.findall(r"\d{1,3}[ \-\']?\d{1,3}[ \-\']?\d{1,3}[,.]\d{2}?", processedText)
    print(moneyArr)
    maxMoney = 0
    maxValue = ""
    minMoney = 10**15
    minDiff  = 10**15
    minValue = ""

    for money in moneyArr:
        value = float(money
                      .replace(" ", "").replace("-", "")
                      .replace("'", "").replace(",", "."))
        if value > maxMoney:
            maxMoney = value
            maxValue = money

    for money in moneyArr:
        value = float(money
                      .replace(" ", "").replace("-", "")
                      .replace("'", "").replace(",", "."))

        if abs(value - maxMoney * 0.19) < minDiff:
            minMoney = value
            minValue = money
            minDiff  = abs(value - maxMoney * 0.19)

    if maxValue != "":
        print("- Total:", maxValue, end=" - ")
        highLightWords([maxValue], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="TOTAL", border_color=MONEY_SUM_CLR)

    if not re.findall(r"(?:НДС не)|(?:[Бб]ез налога НДС)|(?:[Бб]ез НДС)", processedText) and minValue != "":
        print("- Tax:  ", minValue)
        highLightWords([minValue], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="TAX", border_color=MONEY_TAX_CLR)

        
def highLightIDS(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum):    
    print("\nINN/KPP/BIK/BIN:")
    INNKPP = re.findall(r"ИНН ?/ ?КПП:? ?(\d{9,12}) ?/ ?(\d{9})", processedText)

    for inn, kpp in INNKPP:
        print("- INN:", inn)
        highLightWords([inn], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="INN", border_color=INN_CLR)
        print("- KPP:", kpp)
        highLightWords([kpp], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="KPP", border_color=KPP_CLR)

    if len(INNKPP) == 0:
        INN = re.findall(r"ИНН:? ?\d{9,12}", processedText)
        for inn in INN:
            print("- INN:", inn)
            highLightWords([inn], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                           field_type="INN", border_color=INN_CLR)

        KPP = re.findall(r"КПП:? ?\d{8,12}", processedText)
        for kpp in KPP:
            print("- KPP:", kpp)
            highLightWords([kpp], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                           field_type="KPP", border_color=KPP_CLR)

    biks = re.findall(r"БИК:? ?[^ \n]+", processedText)
    for bik_id in biks:
        print("- BIK:", bik_id)
        highLightWords([bik_id], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="BIК", border_color=BIK_CLR)

    bins = re.findall(r"БИН:? ?[^ \n]+", processedText)
    for bin_id in bins:
        print("- BIN:", bin_id)
        highLightWords([bin_id], text_lines, drawnBoxes, xmlsBoxes, pageNum,
                       field_type="BIN", border_color=BIN_CLR)
        


# In[7]:


def combineSimilarBoxes(objects):
    hasChanges = True
    while hasChanges:
        hasChanges = False
        for first_index, first_obj in enumerate(objects):
            if hasChanges:
                break
                
            for second_obj in objects[first_index:]:
                if abs(first_obj["bbox"][1] - second_obj["bbox"][1]) < 1                     and abs(first_obj["bbox"][3] - second_obj["bbox"][3]) < 1:
                    
                    if first_obj == second_obj or first_obj["field_type"] != second_obj["field_type"]:
                        if first_obj["field_type"] == "NUM" and second_obj["field_type"] == "ADDRESS":
                            if second_obj["bbox"][0] - 2 < first_obj["bbox"][0]                                 and second_obj["bbox"][2] + 2 > first_obj["bbox"][0]:
                            
                                objects.remove(first_obj)
                                hasChanges = True
                                break
                                
                        elif first_obj["field_type"] == "ADDRESS" and second_obj["field_type"] == "NUM":
                            if first_obj["bbox"][0] - 2 < second_obj["bbox"][0]                                 and first_obj["bbox"][2] + 2 > second_obj["bbox"][0]:
                                
                                objects.remove(second_obj)
                                hasChanges = True
                                break
                    else:
                        if abs(first_obj["bbox"][0] - second_obj["bbox"][0]) < 10                             or abs(first_obj["bbox"][2] - second_obj["bbox"][2]) < 10                             or abs(first_obj["bbox"][2] - second_obj["bbox"][0]) < 10                             or abs(first_obj["bbox"][0] - second_obj["bbox"][2]) < 10                             or (first_obj["bbox"][0] < second_obj["bbox"][0] and first_obj["bbox"][2] > second_obj["bbox"][0]):
                            
                            if first_obj["text_value"] in second_obj["text_value"]                                 or second_obj["text_value"] in first_obj["text_value"]:
                                continue

                            new_x0 = min(first_obj["bbox"][0], second_obj["bbox"][0])
                            new_x1 = max(first_obj["bbox"][2], second_obj["bbox"][2])
                            new_y0 = min(first_obj["bbox"][1], second_obj["bbox"][1])
                            new_y1 = max(first_obj["bbox"][3], second_obj["bbox"][3])
                            bbox = (new_x0, new_y0, new_x1, new_y1)

                            new_obj = {'field_type': first_obj["field_type"], 
                                       'text_value': first_obj["text_value"] + " " + second_obj["text_value"],
                                       'bbox': bbox, "pageNum": first_obj["pageNum"], "border_color": first_obj["border_color"]}

                            objects.append(new_obj)
                            objects.remove(first_obj)
                            objects.remove(second_obj)
                            hasChanges = True
                            break
    return objects 


def handleNumbers(objects, im_height):
    type_objs = list(filter(lambda obj: obj['field_type'] == 'Number'
                            and obj["bbox"][3] > 0, objects))
    type_objs = sorted(type_objs, key = lambda obj: obj['bbox'][3], reverse=True)
                      
    if len(type_objs) == 0:
        return []
    
    if len(type_objs) > 3:
        type_objs = type_objs[0:3]
        
    if type_objs[0]['bbox'][3] > im_height * 2 / 3:
        type_objs[0]['field_type'] = 'MailIncomeNumber'
    
        for index in range(1, len(type_objs)):
            type_objs[index]['field_type'] = 'Number' + str(index)
    else:
        for index in range(len(type_objs)):
            type_objs[index]['field_type'] = 'Number' + str(index)
        
    return type_objs
 
def handleDates(objects, im_height):
    type_objs = list(filter(lambda obj: obj['field_type'] == 'Date'
                            and obj["bbox"][3] > 0, objects))
    type_objs = sorted(type_objs, key = lambda obj: obj['bbox'][3], reverse=True)
                      
    if len(type_objs) == 0:
        return []
    
    if len(type_objs) > 3:
        type_objs = type_objs[0:3]
        
    if type_objs[0]['bbox'][3] > im_height * 2 / 3:
        type_objs[0]['field_type'] = 'MailIncomeDate'
    
        for index in range(1, len(type_objs)):
            type_objs[index]['field_type'] = 'Date' + str(index)
    else:
        for index in range(len(type_objs)):
            type_objs[index]['field_type'] = 'Date' + str(index)
        
    return type_objs


def handlePersons(objects, im_height):
    top_person_objs = list(filter(lambda obj: (obj["field_type"] == "Person" 
                                        and len(re.findall(r"[А-Я]", obj['text_value'])) >= 3
                                        and len(re.findall(r"[А-Я]", obj['text_value'][0])) == 1
                                        and (len(obj["text_value"].split(" ")) > 1 or len(obj["text_value"].split(".")) > 1)
                                        and obj["bbox"][3] > im_height * 0.6), objects))
    top_person_objs = sorted(top_person_objs, key = lambda obj: obj["bbox"][3], reverse=True)
        
    bottom_person_objs = list(filter(lambda obj: (obj["field_type"] == "Person" 
                                        and len(re.findall(r"[А-Я]", obj['text_value'])) >= 3
                                        and len(re.findall(r"[А-Я]", obj['text_value'][0])) == 1
                                        and (len(obj["text_value"].split(" ")) > 1 or len(obj["text_value"].split(".")) > 1)
                                        and obj["bbox"][3] < im_height * 0.6), objects))
    bottom_person_objs = sorted(bottom_person_objs, key = lambda obj: obj["bbox"][3], reverse=False)
    
    other_person_count = 1
    
    if len(top_person_objs) > 6:
        top_person_objs = top_person_objs[0:6]
        
    for index in range(0, min(3, len(top_person_objs))):
        top_person_objs[index]["field_type"] = "ReceiverPerson" + str(index + 1)
        
    for index in range(3, len(top_person_objs)):
        top_person_objs[index]["field_type"] = "OtherPersons" + str(other_person_count)
        other_person_count += 1
        
    if len(bottom_person_objs) > 6:
        bottom_person_objs = bottom_person_objs[0:6]
        
    for index in range(0, min(3, len(bottom_person_objs))):
        bottom_person_objs[index]["field_type"] = "SenderPerson" + str(min(3, len(bottom_person_objs)) - index)
        
    for index in range(3, len(bottom_person_objs)):
        bottom_person_objs[len(bottom_person_objs) - 1 + 3 - index]["field_type"] = "OtherPersons" + str(other_person_count)
        other_person_count += 1
        
    top_person_objs = list(filter(lambda obj: (obj["field_type"] != "Person"), top_person_objs))
    bottom_person_objs = list(filter(lambda obj: (obj["field_type"] != "Person"), bottom_person_objs))
    
    return top_person_objs + bottom_person_objs


def handleOrgs(objects, im_height, im_width):
    top_orgs_objs = list(filter(lambda obj: (obj["field_type"] == "Org" 
                                            and len(obj["text_value"].split(" ")) > 1
                                            and obj["bbox"][3] > im_height * 0.6), objects))
    top_orgs_objs = sorted(top_orgs_objs, key = lambda obj: obj["bbox"][3], reverse=True)

    bottom_orgs_objs = list(filter(lambda obj: (obj["field_type"] == "Org" 
                                            and len(obj["text_value"].split(" ")) > 1
                                            and obj["bbox"][3] < im_height * 0.6
                                            and obj["bbox"][3] > 0), objects))
    bottom_orgs_objs = sorted(bottom_orgs_objs, key = lambda obj: obj["bbox"][3], reverse=False)
       
    other_org_count = 1
            
    if len(top_orgs_objs) > 1:
        top_left_orgs_objs = list(filter(lambda obj: obj["bbox"][0] < im_width * 0.45, top_orgs_objs))
        top_left_orgs_objs = sorted(top_left_orgs_objs, 
                                    key = lambda obj: obj["bbox"][0], reverse=False)
        
        for index in range(0, min(3, len(top_left_orgs_objs))):
            top_left_orgs_objs[index]["field_type"] = "SenderOrg" + str(index + 1)
            
            
        top_right_orgs_objs = list(filter(lambda obj: obj["bbox"][0] > im_width * 0.45, top_orgs_objs))
        top_right_orgs_objs = sorted(top_right_orgs_objs, 
                                    key = lambda obj: obj["bbox"][0], reverse=False)
        
        for index in range(0, min(3, len(top_right_orgs_objs))):
            top_right_orgs_objs[index]["field_type"] = "ReceiverOrg" + str(index + 1)
        
        top_left_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_left_orgs_objs))
        top_right_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_right_orgs_objs))
        
        return top_left_orgs_objs + top_right_orgs_objs
        
    else:

        if len(top_orgs_objs) > 6:
            top_orgs_objs = top_orgs_objs[0:6]

        for index in range(0, min(3, len(top_orgs_objs))):
            top_orgs_objs[index]["field_type"] = "SenderOrg" + str(index + 1)

        for index in range(3, len(top_orgs_objs)):
            top_orgs_objs[index]["field_type"] = "Orgs" + str(other_org_count)
            other_org_count += 1

#         if len(bottom_orgs_objs) > 6:
#             bottom_orgs_objs = bottom_orgs_objs[0:6]

#         for index in range(0, min(3, len(bottom_orgs_objs))):
#             bottom_orgs_objs[index]["field_type"] = "SenderOrg" + str(min(3, len(bottom_orgs_objs)) - index)

#         for index in range(3, len(bottom_orgs_objs)):
#             bottom_orgs_objs[len(bottom_orgs_objs) - 1 + 3 - index]["field_type"] = "Org" + str(other_org_count)
#             other_org_count += 1

        top_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_orgs_objs))
#         bottom_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), bottom_orgs_objs))

        return top_orgs_objs + bottom_orgs_objs


def saveToXML(objects, docName, images, xml, maxPageNum):    
#     objects = combineSimilarBoxes(objects)

    font = ImageFont.truetype("Arsenal-Regular.otf", 20)

    unique_values = set()
    objects = [o for o in objects
            if o['text_value'] not in unique_values
            and not unique_values.add(o['text_value'])]

    nums_objs = handleNumbers(objects, images[0].size[1])
    dates_objs = handleDates(objects, images[0].size[1])
    
    persons_objs = handlePersons(objects, images[0].size[1])
    orgs_objs = handleOrgs(objects, images[0].size[1], images[0].size[0])
    
    objects = nums_objs + dates_objs + persons_objs + orgs_objs
    
        
    for pageNum in range(0, maxPageNum):
        im_height = images[pageNum].size[1]
        image_drawer = ImageDraw.Draw(images[pageNum])
        
        for obj in objects:
            if obj["pageNum"] != pageNum:
                continue
            
            bbox = (obj["bbox"][0], int(im_height - obj["bbox"][1] - pageNum * 10000),
                    obj["bbox"][2], int(im_height - obj["bbox"][3] - pageNum * 10000))

            image_drawer.rectangle((bbox[0], bbox[1], bbox[2], bbox[3] + random.randint(2, 10)), 
                                    outline=obj["border_color"], width=3)
            
            image_drawer.rectangle((bbox[0], bbox[3], bbox[2], bbox[3]-20), fill="white")

            image_drawer.text((bbox[0], bbox[3]-20), obj["field_type"] + " | " + obj["text_value"], 
                              font = font, fill=obj["border_color"])

            xml.write('  <{field_type} value="{value}" confidence="100" page="{page}" left="{x}" top="{y}" width="{w}" height="{h}"/>'                       .format(field_type=obj["field_type"], value=obj["text_value"].replace('"', '').replace('<', '').replace('>', ''),
                                x=bbox[2], y=bbox[1], w=bbox[2]-bbox[0], h=bbox[1]-bbox[3], page=pageNum)
                      + '\n')
            
        images[pageNum].save("results/" + docName + "_" + str(pageNum) + ".jpg", "JPEG")
        


# In[ ]:


if __name__ == '__main__':
    MODEL_NAME = 'model'
    DPI_SCALE = 4.17
    STANDART_DPI = 72
    PDF_PATH = "input/"
    HANDLED_PATH = "handled/"
    SLEEP_TIME = 5

    ACT_NUM_CLR = "red"
    DATE_CLR = "deepskyblue"
    ADDR_CLR = "darkgoldenrod"
    ORG_CLR = "blue"
    PER_CLR = "green"
    MONEY_SUM_CLR = "limegreen"
    MONEY_TAX_CLR = "salmon"

    INN_CLR = "purple"
    KPP_CLR = "darkviolet"
    BIN_CLR = "violet"
    BIK_CLR = "magenta"

    la_params = LAParams()
#     la_params.line_margin = 1
#     la_params.boxes_flow = 10
    la_params.line_margin = 1.6
    la_params.boxes_flow = 0.5

    createDirIfNotExist(PDF_PATH)
    createDirIfNotExist(HANDLED_PATH)
    createDir("results/", ".jpg")
    createDir("xmls/", ".xml")

    navec = Navec.load('vocab.tar')
    ner = NER.load(MODEL_NAME + '.tar')
    ner.navec(navec)

    while True:
            
        for doc_name in get_files(PDF_PATH, ".pdf"):

#             if doc_name != "7.pdf":
#                 continue

            images = convert_from_path(PDF_PATH + doc_name, dpi = STANDART_DPI * DPI_SCALE)
            
        #     for index, image in enumerate(images):
        #         images[index].save("results/" + doc_name.split(".")[0] + "_" + str(index) + ".jpg")

            fp = open(PDF_PATH + doc_name, 'rb')
            parser = PDFParser(fp)
            document = PDFDocument(parser)
            
            xml = io.open("xmls/" + doc_name.replace('.pdf', '') + ".xml", "w", encoding="utf-8")
            
            xml.write('<?xml version="1.0" encoding="UTF-8"?>' + '\n')
            xml.write('<idcard>' + '\n')

            drawnBoxes = []
            xmlsBoxes = []
            maxPageNum = 0
            
            for pageNum, page in enumerate(PDFPage.create_pages(document)):
                actName = doc_name.split(".")[0] + "_" + str(pageNum) 
        #         if actName != "All_Acts_2_1":
        #             continue
                print(actName)
            
                rawText = ""
                text_lines = []

                
                rsr_mgr = PDFResourceManager()
                device = PDFPageAggregator(rsr_mgr, laparams=la_params)
                
                interpreter = PDFPageInterpreter(rsr_mgr, device)
                interpreter.process_page(page)
                
                layout = device.get_result()
                parse_obj(layout._objs, text_lines)

                processedText = re.sub(r"__+", r" ", rawText)

                if len(processedText) == 0:
                    break

#                 print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
#                 print(processedText)
        #         print("- - - - - - - - - - - - - - - - - -")
        #         for i in range(len(text_lines)):
        #             print(text_lines[i].get_text())
#                 print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
                
                if len(text_lines) == 0:
                    print("No text")
                    print("\n-----------------------------------------------------\n")
                    continue 

                markup = ner(processedText)
                        
                highLightNums(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum)
                highLightDates(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum)
        #         highLightAddresses(processedText, text_lines, drawnBoxes, xmlsBoxes, pageNum)
                highLightOrgs(markup, text_lines, drawnBoxes, xmlsBoxes, pageNum)
                highLightPersons(processedText, markup, text_lines, drawnBoxes, xmlsBoxes, pageNum)
                   
                maxPageNum += 1
                print("\n-----------------------------------------------------\n")
                
            saveToXML(xmlsBoxes, doc_name.replace('.pdf', ''), images, xml, maxPageNum)
            xml.write('</idcard>' + '\n')
            xml.close()

            fp.close()
            move(PDF_PATH + doc_name, HANDLED_PATH + doc_name)

        time.sleep(SLEEP_TIME)

