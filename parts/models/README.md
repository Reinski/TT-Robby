# parts/models/
This folder and its subfolders contain the 3d models used in the project. There may be untested or even obsolete models.  
The parent folder itself contains models that are generally not yet sorted into one of the subfolders. Files from the parent folder will be moved into the appropriate subfolders in the future.  
## Subfolders
- ```./prod/```  
  Contains models that are tested and recommended for use in the machine.
- ```./in_development/```  
  Contains models that are untested or currently in design or test-phase. Use on your own risk.
- ```./templates/```  
  Contains models that are not directly used for the machine, but rather support design process. These can be negatives to substract from other geometries, i.e. they are a slightly oversized, so that the according positives can fit in. Others can be positives which can be re-used when designing new machine parts.

## Conventions
### File Format
As an application and platform independent format, ```.obj``` is preferred. Alternatively ```.stl``` can be used.  
As additional format ```.3mf``` is permitted, as this is also an open format and provides additional benefits - at least for my setup using Windows and a BambuLab printer: Windows Explorer can show a preview for .3mf files and Bambu Studio also uses this format.
### File Names
Naming should basically describe the model. Multiple name-parts are separated by hyphen (-). Multiple words within one name-part should be separated by underscore (_), aka snake-case.  
The following name-parts are obligatory:
- "TT-Robby" (maybe just "TTRobby" in future) has been established as a prefix.
- machine component name
- part specifyer
