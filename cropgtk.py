#!/usr/bin/python3
#    cropgui, a graphical front-end for lossless jpeg cropping
#    Copyright (C) 2009 Jeff Epler <jepler@unpythonic.net>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from cropgui_common import *
from cropgui_common import _

import gi
#from gi.repository import GObject as gobject
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import GLib
#import gtk.glade
from gi.repository import Gdk as gdk
import filechooser
from gi.repository import GdkPixbuf as GdkPixbuf

import sys
import traceback
import imghdr

# otherwise, on hardy the user is shown spurious "[application] closed
# unexpectedly" messages but denied the ability to actually "report [the]
# problem"
def excepthook(exc_type, exc_obj, exc_tb):
    try:
        w = app['window1']
    except NameError:
        w = None
    lines = traceback.format_exception(exc_type, exc_obj, exc_tb)
    print("".join(lines))
    m = gtk.MessageDialog(w,
                gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                gtk.MessageType.ERROR, gtk.ButtonsType.OK,
                _("Stepconf encountered an error.  The following "
                "information may be useful in troubleshooting:\n\n")
                + "".join(lines))
    m.show()
    m.run()
    m.destroy()
sys.excepthook = excepthook

import cropgui_common
gladefile = os.path.join(os.path.dirname(cropgui_common.__file__),
                "cropgui.glade")

class DragManager(DragManagerBase):
    def __init__(self, g):
        self.g = g
        self.idle = None
        self.busy = False

        DragManagerBase.__init__(self)

        w = g['window1']
        i = g['eventbox1']

        i.connect('button-press-event', self.press)
        i.connect('motion-notify-event', self.motion)
        i.connect('button-release-event', self.release)
        w.connect('delete-event', self.close)
        w.connect('key-press-event', self.key)
        g['toolbutton1'].connect('clicked', self.done)
        g['toolbutton2'].connect('clicked', self.escape)
        g['toolbutton3'].connect('clicked', self.ccw)
        g['toolbutton4'].connect('clicked', self.cw)

    def ccw(self, event):
        self.rotate_ccw()
    def cw(self, event):
        self.rotate_cw()

    def coords(self, event):
        return event.x, event.y

    def press(self, w, event):
        if event.type == gdk.EventType._2BUTTON_PRESS:
            return self.done()
        x, y = self.coords(event)
        self.drag_start(x, y, event.state & gdk.ModifierType.SHIFT_MASK)

    def motion(self, w, event):
        x, y = self.coords(event)
        if event.state & gdk.ModifierType.BUTTON1_MASK:
            self.drag_continue(x, y)
        else:
            self.idle_motion(x, y)

    idle_cursor = gdk.Cursor(gdk.CursorType.WATCH)
    cursor_map = {
        DRAG_TL: gdk.Cursor(gdk.CursorType.TOP_LEFT_CORNER),
        DRAG_L: gdk.Cursor(gdk.CursorType.LEFT_SIDE),
        DRAG_BL: gdk.Cursor(gdk.CursorType.BOTTOM_LEFT_CORNER),
        DRAG_TR: gdk.Cursor(gdk.CursorType.TOP_RIGHT_CORNER),
        DRAG_R: gdk.Cursor(gdk.CursorType.RIGHT_SIDE),
        DRAG_BR: gdk.Cursor(gdk.CursorType.BOTTOM_RIGHT_CORNER),
        DRAG_T: gdk.Cursor(gdk.CursorType.TOP_SIDE),
        DRAG_B: gdk.Cursor(gdk.CursorType.BOTTOM_SIDE),
        DRAG_C: gdk.Cursor(gdk.CursorType.FLEUR)}

    def idle_motion(self, x, y):
        i = self.g['image1']
        if not i: return
        if self.busy: cursor = self.idle_cursor
        else:
            what = self.classify(x, y)
            cursor = self.cursor_map.get(what, None)
#        i.window.set_cursor(cursor)

    def release(self, w, event):
        x, y = self.coords(event)
        self.drag_end(x, y)

    def done(self, *args):
        self.result = 1
        self.loop.quit()

    def escape(self, *args):
        self.result = 0
        self.loop.quit()

    def save_and_stay(self, *args):
        self.result = 2
        self.loop.quit()

    def close(self, *args):
        self.result = -1
        self.loop.quit()

    def key(self, w, e):
        if e.keyval == gdk.KEY_Escape: self.escape()
        elif e.keyval == gdk.KEY_Return: self.done()
        elif e.string:
            if e.string == 'n': self.escape()
            elif e.string == 'q': self.close()
            elif e.string == 's': self.save_and_stay()
            elif e.string in ',<': self.rotate_ccw()
            elif e.string in '.>': self.rotate_cw()
            elif e.string in 'h': self.set_crop(self.top, self.left - self.round_x, self.right, self.bottom)
            elif e.string in 'j': self.set_crop(self.top + self.round_y, self.left, self.right, self.bottom)
            elif e.string in 'k': self.set_crop(self.top - self.round_y, self.left, self.right, self.bottom)
            elif e.string in 'l': self.set_crop(self.top, self.left + self.round_x, self.right, self.bottom)
            elif e.string in 'H': self.set_crop(self.top, self.left, self.right - 1, self.bottom)
            elif e.string in 'J': self.set_crop(self.top, self.left, self.right, self.bottom + 1)
            elif e.string in 'K': self.set_crop(self.top, self.left, self.right, self.bottom - 1)
            elif e.string in 'L': self.set_crop(self.top, self.left, self.right + 1, self.bottom)
        # Don't know whether other event handlers need it too, but if
        # this doesn't return True (True prevents further handlers from
        # being invoked), a return somehow double-triggers self.done(),
        # skipping the next image in a multi-file invocation.  Not clear
        # what's going on, but this stops it.
        return True

    def image_set(self):
        self.render()

    def render(self):
        if self.idle is None:
            self.idle = GLib.idle_add(self.do_render)

    def do_render(self):
        if not self.idle:
            return
        self.idle = None

        g = self.g
        i = g['image1']
        if not i:  # app shutting down
            return

        if self.image is None:
            pixbuf = GdkPixbuf.Pixbuf.new_from_data('\0\0\0',
                GdkPixbuf.Colorspace.RGB, 0, 8, 1, 1, 3)
            i.set_from_pixbuf(pixbuf)
            g['pos_left'].set_text('---')
            g['pos_right'].set_text('---')
            g['pos_top'].set_text('---')
            g['pos_bottom'].set_text('---')
            g['pos_width'].set_text('---')
            g['pos_height'].set_text('---')
            g['pos_ratio'].set_text('---')

        else:
            rendered = self.rendered()
            rendered = rendered.convert('RGB')
            i.set_size_request(*rendered.size)
            try:
                image_data = rendered.tostring()
            except:
                image_data = rendered.tobytes()
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(image_data,
                GdkPixbuf.Colorspace.RGB, 0, 8,
                rendered.size[0], rendered.size[1], 3*rendered.size[0])

            tt, ll, rr, bb = self.get_corners()
            ratio = self.describe_ratio()

            g['pos_left'].set_text('%d' % ll)
            g['pos_right'].set_text('%d' % rr)
            g['pos_top'].set_text('%d' % tt)
            g['pos_bottom'].set_text('%d' % bb)
            g['pos_width'].set_text('%d' % (rr-ll))
            g['pos_height'].set_text('%d' % (bb-tt))
            g['pos_ratio'].set_text(self.describe_ratio())

        i.set_from_pixbuf(pixbuf)

        return False


    def wait(self):
        self.loop = GLib.MainLoop()
        self.result = -1
        self.loop.run()
        return self.result

display = gdk.Display().get_default()
wa = display.get_primary_monitor().get_workarea()
max_h = wa.height - 192
max_w = wa.width - 64

class App:
    def __init__(self):
        self.builder = gtk.Builder()
        self.builder.add_from_file(gladefile)
        #self.glade = gtk.glade.XML(gladefile)
        self.drag = DragManager(self)
        self.task = CropTask(self)
        self.dirchooser = None
        self['window1'].set_title(_("CropGTK"))

    def __getitem__(self, name):
        return self.builder.get_object(name)

    def log(self, msg):
        s = self['statusbar1']
        if s:
            s.pop(0)
            s.push(0, msg)
    progress = log

    def set_busy(self, is_busy=True):
        self.drag.busy = is_busy
        i = self['image1']
        if i:
            self.drag.idle_motion(*i.get_pointer())

    def run(self):
        drag = self.drag
        task = self.task

        prev_name = None
        for image_name in self.image_names():
            drag.save_prev_crop()
            self['window1'].set_title(
                _("%s - CropGTK") % os.path.basename(image_name))
            self.set_busy()
            try:
                image = Image.open(image_name)
                drag.round_x, drag.round_y = image_round(image)
                drag.w, drag.h = image.size
                scale = 1
                scale = max (scale, nextPowerOf2((drag.w-1)/(max_w+1)))
                scale = max (scale, nextPowerOf2((drag.h-1)/(max_h+1)))
                thumbnail = image.copy()
                thumbnail.thumbnail((drag.w//scale, drag.h//scale))
            except (IOError,) as detail:
                m = gtk.MessageDialog(self['window1'],
                    gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                    gtk.MessageType.ERROR, gtk.ButtonsType.OK,
                    "Could not open %s: %s" % (image_name, detail))
                m.show()
                m.run()
                m.destroy()
                continue
            image_type = imghdr.what(image_name)
            drag.image = thumbnail
            drag.rotation = 1
            rotation = image_rotation(image)
            if rotation in (3,6,8):
                while drag.rotation != rotation:
                    drag.rotate_ccw()
            drag.scale = scale

            v = 2
            while v == 2:
                self.set_busy(0)
                v = self.drag.wait()
                self.set_busy()
                if v == -1: break      # user closed app
                if v == 0:
                    self.log("Skipped %s" % os.path.basename(image_name))
                    continue           # user hit "next" / escape
                if v == 2: # save but stick with this image
                    target = self.output_name(image_name,image_type,True,prev_name)
                    prev_name = target
                else:
                    target = self.output_name(image_name,image_type)
                if not target:
                    self.log("Skipped %s" % os.path.basename(image_name))
                    continue # user hit "cancel" on save dialog
                task.add(CropRequest(
                    image=image,
                    image_name=image_name,
                    corners=drag.get_corners(),
                    rotation=drag.rotation,
                    target=target,
                ))
            if v == -1: break # user closed app

    def image_names(self):
        if len(sys.argv) > 1:
            for i in sys.argv[1:]: yield i
        else:
            c = filechooser.Chooser(_("Select images to crop"), self['window1'])
            lastdir = None
            while 1:
                files = c.run(lastdir)
                if not files: break
                for i in files:
                    lastdir = os.path.dirname(i)
                    yield i

    def output_name(self, image_name, image_type, chooser=False, prev_name=None):
        image_name = os.path.abspath(image_name)
        i = os.path.basename(image_name)
        if chooser and prev_name is not None:
            d = os.path.dirname(prev_name)
            j = os.path.basename(prev_name)
        else:
            d = os.path.dirname(image_name)
            j = os.path.splitext(i)[0]
            if j.endswith('-crop'): j += os.path.splitext(i)[1]
            else: j += "-crop" + os.path.splitext(i)[1]
            if os.access(d, os.W_OK) and not chooser: return os.path.join(d, j)
        title = _('Save cropped version of %s') % i
        if self.dirchooser is None:
            self.dirchooser = filechooser.DirChooser(title, self['window1'])
        else:
            self.dirchooser.set_title(title)
        self.dirchooser.set_current_folder(d if os.access(d, os.W_OK) else desktop_name())
        self.dirchooser.set_current_name(j)
        r = self.dirchooser.run()
        if not r: return ''
        r = r[0]
        e = os.path.splitext(r)[1]
        if image_type == "jpeg":
            if e.lower() in ['.jpg', '.jpeg']: return r
            return e + ".jpg"
        elif e.lower() == "." + image_type: return r
        else: return e + "." + image_type

app = App()
try:
    app.run()
finally:
    app.task.done()
    del app.task
    del app.drag
