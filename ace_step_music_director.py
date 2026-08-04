"""Antimeter ACE-Step Music Director Tier 2 companion nodes."""
from __future__ import annotations
import json, random, re
from datetime import datetime
from pathlib import Path
import folder_paths
from comfy_api.latest import UI

LANGS=["auto","en","uk","es","fr","de","it","ja","ko","pt","ru","zh","ar","hi","tr","unknown"]
KEYS=[f"{r} {q}" for q in ("major","minor") for r in ("C","C#","Db","D","D#","Eb","E","F","F#","Gb","G","G#","Ab","A","A#","Bb","B")]
BLUEPRINTS={"Auto":("Director chooses from the request",90,"A minor"),"YouTube Background Music":("modern upbeat background music",90,"C major"),"Cinematic Documentary":("cinematic documentary score",90,"D minor"),"Liquid Drum and Bass":("liquid drum and bass",90,"F minor"),"Afro House":("Afro House",90,"A minor"),"Vocal House Club":("vocal house club",120,"E minor"),"Modern Romantic R&B":("modern romantic R&B",120,"C# minor"),"Pop Rock Anthem":("pop-rock anthem",120,"E major"),"Lo-fi Study":("lo-fi hip-hop study music",90,"D minor"),"Trailer / Reveal":("cinematic trailer reveal score",90,"D minor"),"Ambient Sleep / Focus":("ambient sleep and focus soundscape",120,"C major")}
def s(v): return v if isinstance(v,str) else str(v or "")
def n(v,d,a,b):
 try:return max(a,min(b,float(v)))
 except:return d
def i(v,d,a,b):return int(n(v,d,a,b))
def slug(v):return (re.sub(r"[^a-z0-9]+","-",s(v).lower()).strip("-") or "antimeter-track")[:72]
def obj(v):
 text=s(v).strip()
 try:
  x=json.loads(text)
  if isinstance(x,dict):return x
 except:pass
 dec=json.JSONDecoder()
 for m in re.finditer(r"\{",text):
  try:
   x,_=dec.raw_decode(text[m.start():])
   if isinstance(x,dict):return x
  except:pass
 raise ValueError("Director plan is not valid JSON. Re-run Build Music Plan.")
def language(request,target,fallback):
 if target!="auto" and target in LANGS:return target
 q=request.lower()
 for x,y in (("ukrain","uk"),("україн","uk"),("english","en"),("англій","en"),("spanish","es"),("french","fr"),("german","de"),("italian","it"),("japanese","ja"),("korean","ko"),("portuguese","pt"),("russian","ru"),("chinese","zh")):
  if x in q:return y
 return fallback if fallback in LANGS else "en"

class AntimeterMusicDirectorInput:
 @classmethod
 def INPUT_TYPES(cls):
  return {"required":{"request_text":("STRING",{"multiline":True,"default":"Create a 90-second uplifting Afro House track for a sunset travel video, no lyrics, warm percussion, 122 BPM."}),"mode":(["auto","instrumental","song","video_music"],{"default":"auto"}),"video_duration_seconds":("FLOAT",{"default":0.0,"min":0.0,"max":1000.0,"step":0.1}),"target_language":(LANGS,{"default":"auto"}),"variation_count":("INT",{"default":1,"min":1,"max":4}),"quality_profile":(["fast_preview","balanced","final"],{"default":"balanced"}),"seed_policy":(["director","fixed","increment"],{"default":"director"}),"blueprint":(list(BLUEPRINTS),{"default":"Auto"}),"video_structure":(["single_cue","looping_bed","intro_bed_outro","chaptered"],{"default":"single_cue"}),"energy_curve":(["steady","slow_build","drop","calm_ending"],{"default":"steady"})}}
 RETURN_TYPES=("STRING",);RETURN_NAMES=("DIRECTOR_BRIEF",);FUNCTION="run";CATEGORY="Antimeter/Music Director"
 def run(self,request_text,mode,video_duration_seconds,target_language,variation_count,quality_profile,seed_policy,blueprint,video_structure,energy_curve):
  d={"request_text":s(request_text).strip(),"mode":mode,"video_duration_seconds":n(video_duration_seconds,0,0,1000),"target_language":target_language,"variation_count":i(variation_count,1,1,4),"quality_profile":quality_profile,"seed_policy":seed_policy,"blueprint":blueprint,"blueprint_context":BLUEPRINTS[blueprint],"video_structure":video_structure,"energy_curve":energy_curve}
  out=json.dumps(d,ensure_ascii=False,indent=2);return {"ui":{"preview":(out,)},"result":(out,)}

class AntimeterMusicDirectorValidator:
 @classmethod
 def INPUT_TYPES(cls):return {"required":{"director_brief":("STRING",{"forceInput":True,"multiline":True}),"director_plan":("STRING",{"forceInput":True,"multiline":True})}}
 RETURN_TYPES=("STRING","STRING","INT","FLOAT","INT","STRING","STRING","STRING","FLOAT","FLOAT","FLOAT","INT","INT","STRING","STRING","STRING")
 RETURN_NAMES=("MUSIC_PROMPT","LYRICS","SEED","DURATION_SECONDS","BPM","TIME_SIGNATURE","LANGUAGE","KEYSCALE","CFG_SCALE","TEMPERATURE","TOP_P","RECOMMENDED_STEPS","VARIATION_COUNT","FINAL_GENERATION_CARD","VALIDATED_PLAN_JSON","WARNINGS")
 FUNCTION="run";CATEGORY="Antimeter/Music Director"
 def run(self,director_brief,director_plan):
  try:b=obj(director_brief)
  except:b={}
  r=obj(director_plan);warn=[];request=s(b.get("request_text"));mode=s(b.get("mode") or "auto");profile=s(b.get("quality_profile") or "balanced");blue=s(b.get("blueprint") or "Auto");bp=BLUEPRINTS.get(blue,BLUEPRINTS["Auto"])
  low=request.lower();inst=mode=="instrumental" or (mode!="song" and s(r.get("request_type"))!="vocal_song" and (any(x in low for x in ("instrumental","soundtrack","score","background music","no vocals","без вокалу","без слів")) or not any(x in low for x in ("song","lyrics","vocal","sing","rap","пісн","слова","вокал","реп"))))
  video=n(b.get("video_duration_seconds"),0,0,1000);duration=video or n(r.get("duration_seconds"),bp[1],10,1000)
  if video and abs(n(r.get("duration_seconds"),video,10,1000)-video)>1:warn.append(f"Video duration is locked to {video:g} seconds.")
  if profile=="fast_preview" and duration>60:duration=60;warn.append("Fast Preview limits duration to 60 seconds.")
  bpm=i(r.get("bpm"),122 if blue=="Afro House" else 120,40,240)
  if r.get("bpm") in (None,""):warn.append(f"Tempo is missing. The Director selected {bpm} BPM.")
  sig=s(r.get("time_signature") or "4")
  if sig not in ("2","3","4","6"):sig="4";warn.append("Unsupported time signature changed to 4.")
  ks=s(r.get("key") or bp[2]);ks=ks if ks in KEYS else bp[2]
  ln="unknown" if inst else language(request,s(b.get("target_language") or "auto"),s(r.get("language") or "en"))
  lyr="[Instrumental]" if inst else s(r.get("lyrics")).strip()
  if inst and s(r.get("lyrics")).strip() not in ("","[Instrumental]"):warn.append("You asked for no vocals, so Lyrics was set to [Instrumental].")
  if not inst and not lyr:lyr="[Verse]\nOriginal vocal idea\n\n[Chorus]\nWrite your original lyric here";warn.append("Lyrics were omitted. Re-run the plan for finished original lyrics.")
  prompt=s(r.get("music_prompt")).strip()
  if not prompt:prompt=f"{bp[0]}, {bpm} BPM, {sig}/4, {ks}, clear arrangement, polished mix, {'instrumental, no lead vocal' if inst else 'original lead vocal'}";warn.append("Music Prompt was missing. A safe blueprint prompt was supplied.")
  count=i(b.get("variation_count"),1,1,4)
  if profile=="fast_preview" and count>1:count=1;warn.append("Fast Preview uses one variation.")
  seed=i(r.get("seed"),random.randint(1,2000000000),1,2147483647);seedmode=s(r.get("seed_mode") or b.get("seed_policy") or "director")
  if count>1 and seedmode=="director":seedmode="increment";warn.append("A/B variations use an incrementing seed family.")
  if profile=="final" and seedmode=="director":seedmode="fixed";warn.append("Final profile locks a reproducible seed.")
  cfg=n(r.get("cfg_scale"),2,0,10);temp=n(r.get("temperature"),.85,.1,1.5);top=n(r.get("top_p"),.9,0,1);steps=i(r.get("recommended_steps"),12 if profile=="final" else 8,4,40)
  if profile=="fast_preview":steps=min(steps,8)
  typ="instrumental" if inst else ("video_music" if mode=="video_music" else "vocal_song")
  plan={"schema_version":"1.0","request_type":typ,"title_slug":slug(r.get("title_slug") or request or blue),"music_prompt":prompt,"lyrics":lyr,"language":ln,"bpm":bpm,"time_signature":int(sig),"key":ks,"duration_seconds":duration,"seed":seed,"seed_mode":seedmode,"cfg_scale":cfg,"temperature":temp,"top_p":top,"recommended_steps":steps,"variation_count":count,"quality_profile":profile,"blueprint":blue,"video_structure":b.get("video_structure","single_cue"),"energy_curve":b.get("energy_curve","steady"),"generation_notes":r.get("generation_notes") if isinstance(r.get("generation_notes"),list) else [],"warnings":warn+(r.get("warnings") if isinstance(r.get("warnings"),list) else [])}
  card=f"READY — {duration:g} s • {bpm} BPM • {ks} • {typ.replace('_',' ')} • {count} variation{'s' if count!=1 else ''} • {seedmode} seed • {profile}\nTitle: {plan['title_slug']}\nLanguage: {ln} • Time signature: {sig}/4 • Steps: {steps}\nOutput: AntimeterMusicDirector/YYYY-MM-DD/{plan['title_slug']}/"
  if plan["warnings"]:card+="\nPre-flight: "+" | ".join(s(x) for x in plan["warnings"])
  js=json.dumps(plan,ensure_ascii=False,indent=2);wt="\n".join("• "+s(x) for x in plan["warnings"]) or "No pre-flight warnings."
  return {"ui":{"preview":(card,),"status":("READY",)},"result":(prompt,lyr,seed,duration,bpm,sig,ln,ks,cfg,temp,top,steps,count,card,js,wt)}

class AntimeterMusicDirectorSaveMP3:
 @classmethod
 def INPUT_TYPES(cls):return {"required":{"audio":("AUDIO",),"validated_plan_json":("STRING",{"forceInput":True,"multiline":True}),"filename_root":("STRING",{"default":"AntimeterMusicDirector"}),"quality":(["V0","320k","128k"],{"default":"V0"})}}
 RETURN_TYPES=("AUDIO","STRING","STRING");RETURN_NAMES=("audio","AUDIO_PATHS","METADATA_PATHS");FUNCTION="run";CATEGORY="Antimeter/Music Director";OUTPUT_NODE=True
 def run(self,audio,validated_plan_json,filename_root="AntimeterMusicDirector",quality="V0"):
  plan=obj(validated_plan_json);date=datetime.now().strftime("%Y-%m-%d");title=slug(plan.get("title_slug"));ks=s(plan.get("key","A minor")).replace(" ","");prefix=f"{s(filename_root).strip('/\\\\')}/{date}/{title}/{title}_{plan.get('bpm',120)}bpm_{ks}_seed{plan.get('seed',1)}_var%batch_num%"
  ui=UI.AudioSaveHelper.get_save_audio_ui(audio,filename_prefix=prefix,cls=self.__class__,format="mp3",quality=quality);root=Path(folder_paths.get_output_directory());ap=[];mp=[]
  for x,result in enumerate(ui.values):
   path=root/Path(result.subfolder)/result.filename;rel=Path(result.subfolder)/result.filename;actual=dict(plan);actual.update({"creation_time":datetime.now().astimezone().isoformat(timespec="seconds"),"variation_label":f"Variation {chr(65+x)}","audio_path":rel.as_posix(),"sidecar_metadata_path":rel.with_suffix(".metadata.json").as_posix(),"model":"ACE-Step 1.5 Turbo AIO","export_format":"mp3"});path.with_suffix(".plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");meta=path.with_suffix(".metadata.json");meta.write_text(json.dumps(actual,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");ap.append(str(path));mp.append(str(meta))
  return {"ui":ui.as_dict(),"result":(audio,"\n".join(ap),"\n".join(mp))}
NODE_CLASS_MAPPINGS={"AntimeterMusicDirectorInput":AntimeterMusicDirectorInput,"AntimeterMusicDirectorValidator":AntimeterMusicDirectorValidator,"AntimeterMusicDirectorSaveMP3":AntimeterMusicDirectorSaveMP3}
NODE_DISPLAY_NAME_MAPPINGS={"AntimeterMusicDirectorInput":"Antimeter Music Director — User Brief","AntimeterMusicDirectorValidator":"Antimeter Music Director — Plan Validator & Router","AntimeterMusicDirectorSaveMP3":"Antimeter Music Director — Save MP3 + Metadata"}
