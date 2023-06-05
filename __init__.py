import bpy
from bpy.utils import (register_class, unregister_class)
from bpy.types import (Panel, PropertyGroup)
from bpy.props import (EnumProperty, BoolProperty, PointerProperty)

import subprocess
import platform
import os
import sys
addon_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(addon_path)

bl_info = {
    "name": "Translate Text",
    "description": "Translate text in Blender's text editor, using a variety of different online translation services",
    "author": "Theanine3D",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "category": "Text",
    "location": "Text Editor Sidebar (Ctrl + T)",
    "support": "COMMUNITY"
}

# PROPERTY DEFINITIONS

language_items = [
    ("en", "English", "English"),
    ("zh", "Chinese", "Chinese"),
    ("es", "Spanish", "Spanish"),
    ("ar", "Arabic", "Arabic"),
    ("de", "German", "German"),
    ("pt", "Portuguese", "Portuguese"),
    ("ru", "Russian", "Russian"),
    ("fr", "French", "French"),
    ("ja", "Japanese", "Japanese"),
    ("ko", "Korean", "Korean"),
    ("vi", "Vietnamese", "Vietnamese"),
    ("pa", "Punjabi", "Punjabi"),
    ("hi", "Hindi", "Hindi")
]

fast_lang_items = [
    ("en_US", "English", "English"),
    ("zh_CN", "Chinese", "Chinese"),
    ("vi_VN", "Vietnamese", "Vietnamese"),
    ("sk_SK", "Slovak", "Slovak"),
    ("es", "Spanish", "Spanish"),
    ("fr_FR", "French", "French"),
    ("ja_JP", "Japanese", "Japanese")
]

service_items = [
    ("google", "Google", "Google Translate"),
    ("bing", "Bing", "Microsoft Bing Translate"),
    ("baidu", "Baidu", "Baidu Translate"),
    ("sogou", "Sogou", "Sogou"),
]

dependencies_installed = False


class TranslateTextProp(PropertyGroup):
    source_language: EnumProperty(
        items=language_items,
        name="From",
        description="Select a language",
        default="en"
    )
    target_language: EnumProperty(
        items=language_items,
        name="To",
        description="Select a language",
        default="zh"
    )
    translator_service: EnumProperty(
        items=service_items,
        name="Service",
        description="Select a translation service",
        default="google"
    )
    overwrite: BoolProperty(
        name="Overwrite",
        description="If enabled, the translated text will overwrite any text already present in the target text file. If disabled, translated text is appended at the top of the text file",
        default=False
    )
    
# FUNCTION DEFINITIONS


def get_full_langnames(langs):
    lang_names = list()
    for item in language_items:
        if item[0] == langs[0]:
            lang_names.append(item[1])
            break
    for item in language_items:
        if item[0] == langs[1]:
            lang_names.append(item[1])
            break
    return lang_names


def install_dependencies():
    import subprocess
    dependencies = ["translators"]
    python_path = os.path.abspath(sys.executable)
    command = [python_path, "-m", "pip", "install",
               "--target", addon_path] + dependencies
    subprocess.check_call(command)


def check_for_dependencies():
    try:
        global dependencies_installed
        import translators as ts
        import lxml
        import six
        dependencies_installed = True
        return True
    except ModuleNotFoundError:
        print("Dependencies not found. Go into the addon preferences and press the Install Dependencies button.")
        return False


def display_msg_box(message="", title="Info", icon='INFO'):
    ''' Open a pop-up message box to notify the user of something               '''
    ''' Example:                                                                '''
    ''' display_msg_box("This is a message", "This is a custom title", "ERROR") '''

    def draw(self, context):
        lines = message.split("\n")
        for line in lines:
            self.layout.label(text=line)

    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

# CLASS DEFINITION


class TranslatePreferences(bpy.types.AddonPreferences):
    bl_idname = __name__

    toggle_lang1: EnumProperty(
        items=fast_lang_items,
        name="Toggle Language 1",
        description="The 'Toggle Language' operator will switch Blender's UI between this language and the second toggle language",
        default="en_US"
    )
    toggle_lang2: EnumProperty(
        items=fast_lang_items,
        name="Toggle Language 2",
        description="The 'Toggle Language' operator will switch Blender's UI between this language and the first toggle language",
        default="zh_CN"
    )

    def draw(self, context):
        layout = self.layout

        dependencyUI = layout.box()
        row0 = dependencyUI.row()
        row1 = dependencyUI.row()

        langToggleUI = layout.box()
        row2 = langToggleUI.row()
        row3 = langToggleUI.row()

        row0.operator("translate_text.install_dependencies")
        row1.operator("translate_text.open_addon_folder")
        dependencyUI.enabled = not dependencies_installed

        row2.prop(self, "toggle_lang1")
        row3.prop(self, "toggle_lang2")



class TranslateInstallDependencies(bpy.types.Operator):
    """Checks if dependencies are installed, and if they aren't, then the dependencies are installed"""
    bl_idname = "translate_text.install_dependencies"
    bl_label = "Install Dependencies"

    def execute(self, context):
        if not check_for_dependencies():
            install_dependencies()
        return {'FINISHED'}


class OpenAddonFolder(bpy.types.Operator):
    """Opens the addon folder. Useful for cleaning up or removing dependencies"""
    bl_idname = "translate_text.open_addon_folder"
    bl_label = "Open Addon Folder"

    def execute(self, context):
        user_os = platform.system()
        filebrowser_cmd = {
            'Linux': 'xdg-open',
            'Darwin': 'open',
            'Windows': 'explorer'
        }
        print(f'{filebrowser_cmd[user_os]} "{addon_path}"')
        subprocess.call(
            f'{filebrowser_cmd[user_os]} "{addon_path}"', shell=True)
        return {'FINISHED'}


# Translate Text operator


class TranslateText(bpy.types.Operator):
    """Translate text in the currently open text file from one language  to another. The translation is added to a separate text file that is named after the target language"""
    bl_idname = "text.translate_text"
    bl_label = "Translate Text"
    bl_options = {'REGISTER'}

    def execute(self, context):
        if not check_for_dependencies():
            display_msg_box(
                message="You need to install the dependencies first. Open Blender's addon preferences, and find this addon in the list. Then press the Install button.", title="Error", icon='ERROR')
            return {'FINISHED'}

        import translators as ts
        langs = list()
        langs.append(bpy.context.scene.TranslateTextProp.source_language)
        langs.append(bpy.context.scene.TranslateTextProp.target_language)
        service = bpy.context.scene.TranslateTextProp.translator_service
        overwrite = bpy.context.scene.TranslateTextProp.overwrite

        # Get full language names
        lang_names = get_full_langnames(langs)

        # Service-specific tweaks
        if service == 'baidu':
            for lang in langs:
                if lang == "ar":
                    langs[langs.index(lang)] = "ara"
                if lang == "fr":
                    langs[langs.index(lang)] = "fra"
                if lang == "es":
                    langs[langs.index(lang)] = "spa"
                if lang == "ja":
                    langs[langs.index(lang)] = "jp"
                if lang == "ko":
                    langs[langs.index(lang)] = "kor"
                if lang == "vi":
                    langs[langs.index(lang)] = "vie"

        translated_text = ""

        # Make sure we're actually in the text editor first
        area = bpy.context.area
        if area.type == 'TEXT_EDITOR':
            text_block = area.spaces.active.text
            if not language_items[0] in bpy.data.texts.keys():
                text_block.name = lang_names[0]
            else:
                area.spaces.active.text = bpy.data.texts[language_items[0]]

            if text_block.name == language_items[1]:
                text_block.name += ".001"
            if lang_names[0] == lang_names[1]:
                display_msg_box(
                    message="Please choose a different target language.", title="Info", icon='INFO')
                return {'FINISHED'}

            # Ensure that the text file isn't empty first.
            if text_block is not None:
                source_text = text_block.as_string()
                if source_text == "":
                    display_msg_box(
                        message="Text file is empty.", title="Info", icon='INFO')
                    return {'FINISHED'}
                print("\n***********\nTranslating the following text...\n***********\n")
                print(source_text)
                print("\n***********\nfrom " + lang_names[0] + " to " + lang_names[1] +
                      "\n" + "via " + service.capitalize() + "...\n***********\n")

                # Turn off syntax highlighting because the source text isn't a Python script.
                bpy.context.space_data.show_syntax_highlight = False

                # Try translating and catch any exceptions if they occur
                try:
                    translated_text = ts.translate_text(
                        source_text, translator=service, from_language=langs[0], to_language=langs[1])
                except Exception as error:
                    print(
                        f"Error in translation:\n{type(error).__name__}: {error}")
                    display_msg_box(
                        message="Error translating. Try changing the settings and try again.", title="Error", icon='ERROR')

                # Save translated text to new or existing text file
                target_file = None
                for lang in bpy.data.texts.keys():
                    if lang_names[1] == lang:
                        target_file = bpy.data.texts[lang]
                        break
                if target_file is None:
                    target_file = bpy.data.texts.new(lang_names[1])
                if overwrite:
                    target_file.clear()
                target_file.write(translated_text + "\n")

                print(translated_text)
                print(
                    "\n***********\nCheck the text file named after your target language.")
            else:
                display_msg_box(
                    message="Open a text file in the editor first.", title="Info", icon='INFO')
                return {'FINISHED'}

        return {'FINISHED'}

# Reverse languages


class ReverseLanguages(bpy.types.Operator):
    """Reverses the language settings, for quick reverse translation"""
    bl_idname = "text.reverse_langs"
    bl_label = "Reverse"
    bl_options = {'REGISTER'}

    def execute(self, context):
        source_lang = bpy.context.scene.TranslateTextProp.source_language
        target_lang = bpy.context.scene.TranslateTextProp.target_language
        lang_names = get_full_langnames([source_lang, target_lang])
        bpy.context.scene.TranslateTextProp.target_language = source_lang
        bpy.context.scene.TranslateTextProp.source_language = target_lang
        if not lang_names[0] in bpy.data.texts.keys():
            bpy.data.texts.new(lang_names[0])
        if not lang_names[1] in bpy.data.texts.keys():
            bpy.data.texts.new(lang_names[1])

        text_editors = [
            area.spaces[0] for area in bpy.context.screen.areas if area.type == "TEXT_EDITOR"]
        for editor in text_editors:
            if editor.text == bpy.data.texts[lang_names[0]]:
                editor.text = bpy.data.texts[lang_names[1]]
            elif editor.text == bpy.data.texts[lang_names[1]]:
                editor.text = bpy.data.texts[lang_names[0]]
            elif lang_names[0] in editor.text.name:
                editor.text = bpy.data.texts[lang_names[1]]
            elif lang_names[1] in editor.text.name:
                editor.text = bpy.data.texts[lang_names[0]]

        return {'FINISHED'}


# Fast UI Language Toggle operator

class ToggleLangFast(bpy.types.Operator):
    """Instantly toggles Blender's UI language setting between two different languages (set in the addon preferences)"""
    bl_idname = "translate_text.toggle_lang_fast"
    bl_label = "Toggle Language"

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__name__].preferences
        lang1 = prefs.toggle_lang1
        lang2 = prefs.toggle_lang2
        if bpy.context.preferences.view.language == lang1:
            bpy.context.preferences.view.language = lang2
        else:
            bpy.context.preferences.view.language = lang1

        return {'FINISHED'}

ops = (
    TranslateText,
    ReverseLanguages,
    ToggleLangFast
)


def text_editor_menu_item(self, context):
    self.layout.operator("text.translate_text", text="Translate")
 
def menu_func(self, context):
    for op in ops:
        self.layout.operator(op.bl_idname)

# TRANSLATION PANEL

class TranslateText_Panel(Panel):
    bl_label = 'Translate Text'
    bl_idname = "TEXT_PT_translate_text"
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_context = 'text_edit'
    bl_category = 'Translate'

    @ classmethod
    def poll(cls, context):
        return (context.object != None)

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        row0 = layout.row()
        row1 = layout.row()
        row2 = layout.row()
        row3 = layout.row()
        row4 = layout.row()
        row5 = layout.row()
        row0.prop(bpy.context.scene.TranslateTextProp, "source_language")
        row1.prop(bpy.context.scene.TranslateTextProp, "target_language")
        row2.operator("text.reverse_langs")
        row3.prop(bpy.context.scene.TranslateTextProp, "translator_service")
        row4.prop(bpy.context.scene.TranslateTextProp, "overwrite")
        row5.operator("text.translate_text")

# End of classes


classes = (
    TranslateText_Panel,
    TranslateTextProp,
    TranslateText,
    ToggleLangFast,
    ReverseLanguages,
    TranslatePreferences,
    TranslateInstallDependencies,
    OpenAddonFolder
)

def register():
    for cls in classes:
        register_class(cls)
    bpy.types.Scene.TranslateTextProp = PointerProperty(
        type=TranslateTextProp)
    bpy.types.TEXT_MT_editor_menus.append(text_editor_menu_item)

def unregister():
    for cls in classes:
        unregister_class(cls)
    del bpy.types.Scene.TranslateTextProp
    bpy.types.TEXT_MT_editor_menus.remove(text_editor_menu_item)


if __name__ == "__main__":
    register()
