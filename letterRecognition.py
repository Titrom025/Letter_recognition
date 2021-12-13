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

# import extractors


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


RECEIVER_ORGS = {'заслон':'АО «Заслон»'}
RECEIVER_PERSONS = []

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
        field_type=field_type, border_color=border_color
    )
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

def highlightObjects(objects, field_type):
#   print("\nHighlight", field_type)
  for words in objects:
    # print(' '.join(words))
    highLightWords(words, text_lines, drawnBoxes, xmlsBoxes, pageNum,
     field_type=field_type, border_color=border_colors[field_type])

def combineSimilarBoxes(objects):
  hasChanges = True
  while hasChanges:
    hasChanges = False
    for first_index, first_obj in enumerate(objects):
      if hasChanges:
        break
        
      for second_obj in objects[first_index:]:
        if abs(first_obj["bbox"][1] - second_obj["bbox"][1]) < 1 \
          and abs(first_obj["bbox"][3] - second_obj["bbox"][3]) < 1:
          
          if first_obj == second_obj or first_obj["field_type"] != second_obj["field_type"]:
            if first_obj["field_type"] == "NUM" and second_obj["field_type"] == "ADDRESS":
              if second_obj["bbox"][0] - 2 < first_obj["bbox"][0] \
                and second_obj["bbox"][2] + 2 > first_obj["bbox"][0]:
              
                objects.remove(first_obj)
                hasChanges = True
                break
                
            elif first_obj["field_type"] == "ADDRESS" and second_obj["field_type"] == "NUM":
              if first_obj["bbox"][0] - 2 < second_obj["bbox"][0] \
                and first_obj["bbox"][2] + 2 > second_obj["bbox"][0]:
                
                objects.remove(second_obj)
                hasChanges = True
                break
          else:
            if abs(first_obj["bbox"][0] - second_obj["bbox"][0]) < 10 \
              or abs(first_obj["bbox"][2] - second_obj["bbox"][2]) < 10 \
              or abs(first_obj["bbox"][2] - second_obj["bbox"][0]) < 10 \
              or abs(first_obj["bbox"][0] - second_obj["bbox"][2]) < 10 \
              or (first_obj["bbox"][0] < second_obj["bbox"][0] and first_obj["bbox"][2] > second_obj["bbox"][0]):
              
              if first_obj["text_value"] in second_obj["text_value"] \
                or second_obj["text_value"] in first_obj["text_value"]:
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
    type_objs[0]['field_type'] = 'MailOutcomeNumber'
  
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
    type_objs[0]['field_type'] = 'MailOutcomeDate'
  
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
  objects_to_handle = objects.copy()
  receiver_objs = []
  for obj in objects:
    for receier_org_short in RECEIVER_ORGS:
      if receier_org_short in obj['text_value'].lower():
        obj['text_value'] = RECEIVER_ORGS[receier_org_short]
        receiver_objs.append(obj)
        
  objects_to_handle = [obj for obj in objects if obj not in receiver_objs]

  for index in range(len(receiver_objs)):
      receiver_objs[index]['field_type'] = 'ReceiverOrg' + str(index + 1)



  top_orgs_objs = list(filter(lambda obj: (obj["field_type"] == "Org" 
                      and (len(obj["text_value"].split(" ")) > 1 or len(obj["text_value"].split("«")) > 1)
                      and obj["bbox"][3] > im_height * 0.6), objects_to_handle))
  top_orgs_objs = sorted(top_orgs_objs, key = lambda obj: obj["bbox"][3], reverse=True)

  bottom_orgs_objs = list(filter(lambda obj: (obj["field_type"] == "Org" 
                      and len(obj["text_value"].split(" ")) > 1
                      and obj["bbox"][3] < im_height * 0.6
                      and obj["bbox"][3] > 0), objects_to_handle))
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
    
    for index in range(0 + len(receiver_objs), min(3, len(top_right_orgs_objs))):
      top_right_orgs_objs[index]["field_type"] = "ReceiverOrg" + str(index + 1)
    
    top_left_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_left_orgs_objs))
    top_right_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_right_orgs_objs))
    
    return top_left_orgs_objs + top_right_orgs_objs + receiver_objs
    
  else:

    if len(top_orgs_objs) > 6:
      top_orgs_objs = top_orgs_objs[0:6]

    for index in range(0, min(3, len(top_orgs_objs))):
      top_orgs_objs[index]["field_type"] = "SenderOrg" + str(index + 1)

    for index in range(3, len(top_orgs_objs)):
      top_orgs_objs[index]["field_type"] = "Orgs" + str(other_org_count)
      other_org_count += 1

    top_orgs_objs = list(filter(lambda obj: (obj["field_type"] != "Org"), top_orgs_objs))

    return top_orgs_objs + bottom_orgs_objs + receiver_objs


def saveToXML(objects, docName, images, xml, maxPageNum):  
  font = ImageFont.truetype("Arsenal-Regular.otf", 20)

  unique_values = set()
  objects = [o for o in objects
      if (o['text_value'], o['field_type']) not in unique_values
      and not unique_values.add((o['text_value'], o['field_type']))]

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

      xml.write('  <{field_type} value="{value}" confidence="100" page="{page}" left="{x}" top="{y}" width="{w}" height="{h}"/>' \
            .format(field_type=obj["field_type"], value=obj["text_value"].replace('"', '').replace('<', '').replace('>', ''),
                x=bbox[2], y=bbox[1], w=bbox[2]-bbox[0], h=bbox[1]-bbox[3], page=pageNum)
            + '\n')
      
    images[pageNum].save("results/" + docName + "_" + str(pageNum) + ".jpg", "JPEG")
    
if __name__ == '__main__':
  MODEL_NAME = 'model'
  DPI_SCALE = 4.17
  STANDART_DPI = 72
  PDF_PATH = "input/"
  HANDLED_PATH = "handled/"
  SLEEP_TIME = 5

  border_colors = {
    'Number': 'red',
    'Date': 'deepskyblue',
    'Org': 'blue',
    'Person': 'green'
  }

  la_params = LAParams()
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
      images = convert_from_path(PDF_PATH + doc_name, dpi = STANDART_DPI * DPI_SCALE)

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

        # print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        # if len(processedText) == 0:
        #   print("No text")
        # else:
        #   print(processedText)
        # print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<\n")
        


        if len(processedText) == 0:
          break

        markup = ner(processedText)
            
        extracted_nums = extractNums(processedText)
        highlightObjects(extracted_nums, 'Number')

        extracted_dates = extractDates(processedText)
        highlightObjects(extracted_dates, 'Date')

        extracted_orgs, extracted_persons = extractOrgs(markup)
        highlightObjects(extracted_orgs, 'Org')
        highlightObjects(extracted_persons, 'Person')

        extracted_persons = extractPersons(processedText, markup)
        highlightObjects(extracted_persons, 'Person')
           
        maxPageNum += 1
        
      saveToXML(xmlsBoxes, doc_name.replace('.pdf', ''), images, xml, maxPageNum)
      xml.write('</idcard>' + '\n')
      xml.close()

      fp.close()
      move(PDF_PATH + doc_name, HANDLED_PATH + doc_name)

    time.sleep(SLEEP_TIME)