# -*- coding:utf-8 -*-
# Galicaster, Multistream Recorder and Player
#
#       galicaster/classui/recorderui
#
# Copyright (c) 2011, Teltek Video Research <galicaster@teltek.es>
#
# This work is licensed under the Creative Commons Attribution-
# NonCommercial-ShareAlike 3.0 Unported License. To view a copy of 
# this license, visit http://creativecommons.org/licenses/by-nc-sa/3.0/ 
# or send a letter to Creative Commons, 171 Second Street, Suite 300, 
# San Francisco, California, 94105, USA.

from os import path
import gobject
import gst
import gtk
import time
import datetime
import logging
#import thread
from threading import Thread as thread
import pango

from galicaster.mediapackage import mediapackage
from galicaster.recorder import Recorder
from galicaster.classui.metadata import MetadataClass as Metadata
from galicaster import context
from galicaster.classui.statusbar import StatusBarClass
from galicaster.classui.audiobar import AudioBarClass
from galicaster.classui.events import EventManager
from galicaster.classui import message

gtk.gdk.threads_init()
log = logging.getLogger()

#ESTADOS
GC_EXIT = -1
GC_INIT = 0
GC_READY = 1
GC_PREVIEW = 2
GC_RECORDING = 3
GC_REC2 = 4
GC_PAUSED = 5
GC_STOP = 6
GC_BLOCKED = 7

class RecorderClassUI(gtk.Box):
    """
    Graphic User Interface for Record alone
    """

    __gtype_name__ = 'RecorderClass'

    def __init__(self, package=None): 
  
        log.info("Creating Recording Area")
        gtk.Box.__init__(self)
	builder = gtk.Builder()
        builder.add_from_file(path.join(path.dirname(path.abspath(__file__)), 'recorder.glade'))
       
        self.repo = context.get_repository()
        self.dispatcher = context.get_dispatcher()
        self.current_mediapackage = None
        self.current = None
        self.next = None
        self.restarting = False
        self.normal_style = None
        self.font = None
        self.scheduled_recording = False
        self.focus_is_active = False
        self.no_audio = False
        self.no_audio_dialog = None

        # BUILD
        self.recorderui = builder.get_object("recorderbox")
        self.area1 = builder.get_object("videoarea1")
        self.area2 = builder.get_object("videoarea2")
        self.area1.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        self.area2.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))

        self.vubox = builder.get_object("vubox")
        self.gui = builder

        # STATUS BAR
        self.statusbar=StatusBarClass()
        self.dispatcher.connect("update-rec-status", self.statusbar.SetStatus)
        self.dispatcher.connect("update-video", self.statusbar.SetVideo)
        
        self.statusbar.SetTimer(0)

        # VUMETER
        self.audiobar=AudioBarClass()

        # UI
        self.vubox.add(self.audiobar.bar)
        self.pack_start(self.recorderui,True,True,0)

        # Event Manager
        self.dispatcher.connect("start-before", self.on_start_before)
        self.dispatcher.connect("restart-preview", self.on_restart_preview)
        self.dispatcher.connect("galicaster-status", self.event_change_mode)
        self.dispatcher.connect("update-rec-vumeter", self.audiobar.SetVumeter)
        self.dispatcher.connect("audio-mute", self.warning_audio)
        self.dispatcher.connect("audio-recovered", self.warning_audio_destroy)
        self.dispatcher.connect("galicaster-quit", self.close)

        # STATES
        self.status = GC_INIT
        self.previous = None
        self.change_state(GC_INIT)

        # PERMISSIONS
        self.conf = context.get_conf()
        self.allow_pause = self.conf.get_permission("pause")
        self.allow_start = self.conf.get_permission("start")
        self.allow_stop = self.conf.get_permission("stop")
        self.allow_manual = self.conf.get_permission("manual")
        self.allow_overlap = self.conf.get_permission("overlap")
     
        # OTHER
        builder.connect_signals(self)

        self.change_state(GC_READY)

        self.on_start()

        # SCHEDULER FEEDBACK
        self.scheduler_thread_id = 1
        self.clock_thread_id = 1
        self.start_thread_id = None

        self.scheduler_thread = thread(target=self.scheduler_launch_thread)
        self.clock_thread = thread(target=self.clock_launch_thread)
        self.scheduler_thread.daemon = True
        self.clock_thread.daemon = True
        self.scheduler_thread.start()
        self.clock_thread.start()
        
        


    #def do_expose_event(self, event): # FIXME introduce expose_event if neccesary
    #    print "do_expose_event"
    #    if self.imagesink:
            #self.imagesink.expose()
        #    return False
        #else:
        #    return True

    def select_devices(self):
        log.info("Setting Devices")
        self.mediapackage = self.repo.get_new_mediapackage()
        self.mediapackage.setTitle("Recording started at "+ datetime.datetime.now().replace(microsecond = 0).isoformat())#FIXME
        bins = self.conf.getBins(self.repo.get_attach_path())
        # FIMXE indicate proper areas by device name
        areas = { self.conf.get("screen", "left") : self.area1, self.conf.get("screen","right") : self.area2 } 
        self.record = Recorder(bins, areas) 
        self.record.mute_preview(not self.focus_is_active)

#------------------------- PLAYER ACTIONS ------------------------

    def on_start(self, button=None):
        """Preview at start"""
        log.info("Starting Preview")
        self.conf.reload()
        self.select_devices()
        self.record.preview()
        self.change_state(GC_PREVIEW)
        return True

    def on_restart_preview(self, button=None, element=None): 
        """Restarting preview, commanded by record""" 
        log.info("Restarting Preview")
        self.conf.reload()
        self.select_devices()
        self.record.preview()
        self.change_state(GC_PREVIEW)
        self.restarting = False
        return True

    def on_rec(self,button=None): 
        """Manual Recording """
        log.info("Recording")
        self.record.record()
        self.mediapackage.status=mediapackage.RECORDING
        self.mediapackage.setDate(datetime.datetime.utcnow().replace(microsecond = 0))
        self.clock=self.record.get_clock()
        # self.timer_thread_id = thread.start_new_thread(self.timer_thread, ()) #TODO timer thread
        self.timer_thread_id = 1
        self.timer_thread = thread(target=self.timer_launch_thread) #TODO timer thread
        self.timer_thread.daemon = True
        self.timer_thread.start()
        self.change_state(GC_RECORDING)
        return True  

    def on_start_before(self, origin, key):
        """ Start a recording before its schedule """
        log.info("Start recording before schedule")
        #self.conf.reload()
        self.mediapackage = self.repo.get(key)
        self.mediapackage.manual = True      
        #self.mediapackage.__duration=None
        #self.scheduler
        #self.next_dialog.destroy()      

        self.on_rec()

        #print "TODO del stop_timer if necesary"

        return True  
          

    def on_pause(self,button):
        #print button
        if self.status == GC_PAUSED:
            log.debug("Resuming Recording")
            self.change_state(GC_RECORDING)
            self.record.resume()
        elif self.status == GC_RECORDING:
            log.debug("Pausing Recording")
            self.change_state(GC_PAUSED)
            self.record.pause()
            guifile = path.join(path.dirname(path.abspath(__file__)),"paused.glade")
            gui = gtk.Builder()
            gui.add_from_file(guifile)    
            dialog = gui.get_object("dialog") 
            self.pause_dialog=dialog
            image = gui.get_object("image") 
            button = gui.get_object("button") 
            dialog.set_transient_for(self.get_toplevel())
    
            response = dialog.run()
            if response == 1:
                self.on_pause(None)
                #log.debug("Resuming Recording")
                #self.change_state(GC_RECORDING)
                #self.record.resume()
            dialog.destroy()                
            
    def on_stop(self,button):
        # FIXME if its not scheduled

        text = {"title" : "Stop",
              "main" : "Are you sure you want to\nstop the recording?",
			}
        buttons = ( "Stop", gtk.RESPONSE_OK, gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)
        size = [ self.window.get_screen().get_width(), self.window.get_screen().get_height() ]
        warning = message.PopUp(message.WARNING, text, size, 
					self.get_toplevel(), buttons)

        
        if warning.response in message.POSITIVE:
            self.close_recording() 

    def close_recording(self):
        """
        Set the final data on the mediapackage, stop the record and restart the preview
        """
        duration = (self.clock.get_time()-self.initial_time)*1000/gst.SECOND  
        self.record.stop_record_and_restart_preview()
        self.change_state(GC_STOP)

        if self.conf.get('ingest', 'active') == "True" and self.conf.get('ingest', 'default') == "True":
            self.mediapackage.status = mediapackage.PENDING
            log.info("Stop and Ingest Recording")
        else:
            self.mediapackage.status = mediapackage.RECORDED
            log.info("Stop Recording")

        self.repo.add_after_rec(self.mediapackage, self.record.bins_desc, duration)
        self.timer_thread_id = None
        #self.timer_thread_id.join()
       

    def on_scheduled_start(self, source, identifier): # FIXME get in a thread
        log.info("Scheduled Start")
        self.conf.reload()
        self.current_mediapackage = identifier
        self.scheduled_recording = True
        self.mediapackage = self.repo.get(identifier)

        #thread.start_new_thread(self.start_thread, (identifier,))
        a=thread(target=self.start_thread, args=(identifier,))
        a.daemon = False
        a.start()


    def start_thread(self,identifier): #FIXME set as private_
        # FIXME the core should know if the recording its scheduled, 
        #print identifier
        self.start_thread_id = 1
        if self.status == GC_PREVIEW: # Record directly
            self.on_rec() 
        
        elif self.status in [ GC_RECORDING, GC_PAUSED ] :

            if self.allow_overlap: 
                pass
                # TODO: dont stop and extend recording until the end of the new interval
                # In case of stop, restart with the overlapped job

            else: # Stop current recording, wait until prewiew restarted and record
                self.restarting = True
                self.close_recording()                
                while self.restarting:
                    time.sleep(0.1) 
                    if self.start_thread_id == None:
                        return                    
                self.on_rec()       
                      
        elif self.status == GC_INIT:  # Start Preview and Record
            self.on_start()
            while self.record.get_status() != gst.STATE_PLAYING:
                time.sleep(0.2)
                if self.start_thread_id == None:
                    return
            self.on_rec()

        title = self.repo.get(identifier).title
        self.dispatcher.emit("update-video", title)
        
        return None

    def on_scheduled_stop(self,source,identifier):
        log.info("Scheduled Stop")
        self.current_mediapackage = None
        self.close_recording()
        self.scheduled_recording = False


    def reload_state_and_permissions(self):
        """
        Force a state review in case permissions had changed
        """
        self.conf.reload()
        self.allow_pause = self.conf.get_permission("pause")
        self.allow_start = self.conf.get_permission("start")
        self.allow_stop = self.conf.get_permission("stop")
        self.allow_manual = self.conf.get_permission("manual")
        self.allow_overlap = self.conf.get_permission("overlap")
        self.change_state(self.status)

    def reload_state(self):
        """
        Force a state review in case situation had changed
        """
        self.change_state(self.status)



    def on_help(self,button):
        log.info("Help requested")   

        text = {"title" : "Help",
                "main" : " Visit galicaster.teltek.es",
                "text" : " ...or contact us on our community list."
			}
        # buttons = (gtk.STOCK_OK, gtk.RESPONSE_OK)
        buttons = None
        size = [ self.window.get_screen().get_width(), self.window.get_screen().get_height() ]
        warning = message.PopUp(message.INFO, text, size, 
                                self.get_toplevel(), buttons)

    def restart(self): # FIXME name confusing cause on_restart_preview
        """
        Called by Core, if in preview, reload configuration and restart preview
        """
        if self.status == GC_STOP:
            self.on_start()
            
        elif self.status == GC_PREVIEW:
            self.change_state(GC_STOP)
            self.record.just_restart_preview() #FIXME merge just_rp and stop_record_and_rp
        else:
            log.warning("Restart preview called while Recording")

        return True

        

    def on_quit(self,button=None): 
        gui = gtk.Builder()
        gui.add_from_file(path.join(path.dirname(path.abspath(__file__)), 'quit.glade'))
        dialog = gui.get_object("dialog")
        dialog.set_transient_for(self.get_toplevel())

        response =dialog.run()
        if response == gtk.RESPONSE_OK:   
            dialog.destroy()
            if self.status >= GC_PREVIEW:
                self.record.stop_preview()

            self.change_state(GC_EXIT)
            log.info("Closing Clock and Scheduler")

            self.scheduler_thread_id = None
            self.clock_thread = None # FIXME close threads for sure
            #self.scheduler_thread.join()
            #self.clock_thread.join()
            
            self.emit("delete_event", gtk.gdk.Event(gtk.gdk.DELETE))    
        else:
            dialog.destroy()
            
        return True

#------------------------- THREADS ------------------------------
 
    def timer_launch_thread(self):
        """
        Based on: http://pygstdocs.berlios.de/pygst-tutorial/seeking.html
        """
        thread_id= self.timer_thread_id
        self.initial_time=self.clock.get_time()
        self.initial_datetime=datetime.datetime.utcnow().replace(microsecond = 0)
        gtk.gdk.threads_enter()
        self.statusbar.SetTimer(0)
        gtk.gdk.threads_leave()
              
        while thread_id == self.timer_thread_id:            
        #while True:
            actual_time=self.clock.get_time()               
            timer=(actual_time-self.initial_time)/gst.SECOND
            if thread_id==self.timer_thread_id:
                gtk.gdk.threads_enter()
                self.statusbar.SetTimer(timer)
                gtk.gdk.threads_leave()
            time.sleep(0.2)          
        return True

    def scheduler_launch_thread(self):
        """
        Based on: http://pygstdocs.berlios.de/pygst-tutorial/seeking.html
        """
        thread_id= self.scheduler_thread_id
        event_type = self.gui.get_object("nextlabel")#FIXME change name
        title = self.gui.get_object("titlelabel")#FIXME change name
        status = self.gui.get_object("eventlabel")# FIXME idem 
        #more_events = self.gui.get_object("morelabel")# FIXME idem 
        frame = self.gui.get_object("framebox")#FIXME change name
        frame2 = self.gui.get_object("framebox2")#FIXME change name
        #frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("gray"))
        frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_from_hsv(0,0,0.73))
        frame2.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_from_hsv(0,0,0.73))

        self.check_schedule() # actualiza o mp actual e o proximo, se os hai
        parpadeo = True
        changed = False
        
        if self.font == None:
            anchura = self.get_toplevel().get_screen().get_width()
            if anchura not in [1024,1280,1920]:
                anchura = 1920            
            k = anchura / 1920.0
            self.font = pango.FontDescription("bold "+str(k*42))        
        status.modify_font(self.font) # FIXME change font size if screen is smaller
        self.style_normal = status.rc_get_style()
        status.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
        self.style_red = status.rc_get_style()
        status.set_style(self.style_normal)

        while thread_id == self.scheduler_thread_id:
        #while True:
            if self.current:
                start = self.current.getLocalDate()
                duration = self.current.getDuration() / 1000
                end = start + datetime.timedelta(seconds=duration)
                dif = end - datetime.datetime.now()
                #more_events.set_text("[+]")
                status.set_text("Stopping on "+self.time_readable(dif))
                event_type.set_text("Current REC:") 
                title.set_text(self.current.title)
                if dif < datetime.timedelta(0,50):
                    if not changed:
                        status.set_style(self.style_red)
                        changed = True
                elif changed:
                    status.set_style(self.style_normal)
                    changed = False
                if dif < datetime.timedelta(0,10):
                    if parpadeo:
                        status.set_text("")
                        parpadeo =  False
                    else:
                        parpadeo = True
                # Timer(diff,self.check_schedule)

            elif self.next:
                start = self.next.getLocalDate()
                dif = start - datetime.datetime.now()
                #more_events.set_text("[+]")
                event_type.set_text("Next REC:")
                title.set_text(self.next.title)
                status.set_text("Starting on " + self.time_readable(dif))
                if dif < datetime.timedelta(0,60):
                    if not changed:
                        status.set_style(self.style_red)
                        #status.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
                        changed = True
                elif changed:
                    status.set_style(self.style_normal)
                    changed = False

                if dif < datetime.timedelta(0,20):
                    if parpadeo:
                        status.set_text("")
                        parpadeo =  False
                    else:
                        parpadeo = True
                # Timer(60,self.check_schedule)
            else: # nothing
                #more_events.set_text("")
                event_type.set_text("")
                status.set_text("")
                title.set_text("No upcoming events")

            time.sleep(0.5)
            self.check_schedule()
            
        return True

    def clock_launch_thread(self):
        """
        Based on: http://pygstdocs.berlios.de/pygst-tutorial/seeking.html
        """
        thread_id= self.clock_thread_id
        clock = self.gui.get_object("local_clock")# FIXME idem 
        #frame = self.gui.get_object("clock_frame")# FIXME idem 
        #frame.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_from_hsv(0,0,0.73))

        while thread_id == self.clock_thread_id:            
        #while True:
            if thread_id==self.clock_thread_id:
                clocktime = datetime.datetime.now().time().strftime("%H:%M")
                clock.set_label(clocktime)
            time.sleep(1)          
        return True


    def time_readable(self, timedif):
        """
        Take a timedelta and return it formatted
        """       
           
        if timedif < datetime.timedelta(0,300): # ata 5 minutos
            formatted = "{minutes:02d}:{seconds:02d}".format( # FIXME maybe :02d
                            minutes = timedif.seconds // 60, 
                            seconds = timedif.seconds % 60 )
        elif timedif < datetime.timedelta(1,0): # ata 24 horas
            formatted = "{hours:02d}:{minutes:02d}:{seconds:02d}".format(
                hours =  timedif.days*24 + timedif.seconds // 3600, 
                minutes = timedif.seconds % 3600 // 60 ,
                seconds = timedif.seconds % 60 
                )
        else: # dias
            today = datetime.datetime.now()
            then = today + timedif
            dif = then.date() - today.date()
            formatted = "{days} day{plural}".format(
                days =  dif.days,
                plural = 's' if dif.days >1 else '')

        return formatted
    
   
    def check_schedule(self):
        previous1 = self. current
        previous2 = self.next
        if self.current_mediapackage == None:
            self.current = None
        else:
            self.current = self.repo.get(self.current_mediapackage)
        previous2 = self.next
        self.next = self.repo.get_next_mediapackage() # could be None
        if previous2 != self.next:
            self.reload_state()

#------------------------- POPUP ACTIONS ------------------------

    def on_edit_meta(self,button):
        self.change_state(GC_BLOCKED) #FIXME not neccesary, check downwards
        if not self.scheduled_recording:
            meta=Metadata(self.mediapackage, parent=self)
            # FIXME create a proper meta for this area
            self.statusbar.SetVideo(None,self.mediapackage.metadata_episode['title'])
            self.statusbar.SetPresenter(None,self.mediapackage.creators)
        self.change_state(self.previous)  
        return True #  FIXME return False if its not oppened?      

    def show_next(self,button=None,tipe = None):   
        eventm=EventManager(parent=self)
        return True

    def show_about(self,button=None,tipe = None):
        gui = gtk.Builder()
        gui.add_from_file(path.join(path.dirname(path.abspath(__file__)), 'about.glade'))
        dialog = gui.get_object("dialog")
        dialog.set_transient_for(self.get_toplevel())
    
        response = dialog.run()
        if response:
            dialog.destroy()
        else:
            dialog.destroy()
        return True


    def warning_audio(self, element=None): # TODO make it generic
        self.no_audio = True
        if self.focus_is_active and self.no_audio_dialog == None:
            gui = gtk.Builder()
            gui.add_from_file(path.join(path.dirname(path.abspath(__file__)), "warning.glade"))
            self.no_audio_dialog = gui.get_object("dialog")
            self.no_audio_dialog.set_transient_for(self.get_toplevel())
            self.no_audio_dialog.show() 
        return True


    def warning_audio_destroy(self, element=None):
        self.no_audio = False
        try:
            assert self.no_audio_dialog
        except:
            return True           
        self.no_audio_dialog.destroy()
        self.no_audio_dialog = None
        return True      
    
#-------------------------- UI ACTIONS -----------------------------

    def event_change_mode(self, orig, old_state, new_state):
        if new_state == 0: # and self.no_audio:
            self.focus_is_active = True
            if self.no_audio:
                self.warning_audio()
            #if self.pipeline_started:
            self.record.mute_preview(False)

        if old_state == 0:
            self.focus_is_active = False

            if self.no_audio:
                self.no_audio_dialog.destroy()
                self.no_audio_dialog = None
            #if self.pipeline_started:
            self.record.mute_preview(True)


    def change_mode(self, button):
        # 0 rec 1 list 2 player
        self.dispatcher.emit("change-mode", 3) # FIXME use constant

    def resize(self,size): # FIXME change alignments and 
        altura = size[1]
        anchura = size[0]
        
        k = anchura / 1920.0 # we assume 16:9 or 4:3?
        self.proportion = k

        #Recorder
        clock = self.gui.get_object("local_clock")#4
        big = self.gui.get_object("bigstatus")#4
        #big2 = self.gui.get_object("bigstatus2")#4
        logo = self.gui.get_object("classlogo")       
        next = self.gui.get_object("nextlabel")#2.8
        more = self.gui.get_object("morelabel")#3.5 << menos
        #listl = self.gui.get_object("listlabel")#3.5
        title = self.gui.get_object("titlelabel")#2.5
        eventl = self.gui.get_object("eventlabel")#3.5
        align2r = self.gui.get_object("top_align")
        pbox = self.gui.get_object("prebox")

        #buf=logo.get_pixbuf()
        #hlogo=buf.get_property("height")
        
        def relabel(label,size,bold):           
            if bold:
                modification = "bold "+str(size)
            else:
                modification = str(size)
            label.modify_font(pango.FontDescription(modification))

        def relabel2(label,size,bold):           
            if bold:
                modification = "bold "+str(size)
            else:
                modification = str(size)
            self.font = pango.FontDescription(modification)     
            label.modify_font(self.font)
            
            #label.modify_font(pango.FontDescription(modification))
            #self.font=pango.FontDescription(modification)
            #label.modify_font(self.font)


        relabel(clock,k*25,False)
        relabel(big,k*48,True)
        #relabel(big2,k*48,True)
        image=gtk.gdk.pixbuf_new_from_file(path.join(path.dirname(path.abspath(__file__)), "logo"+str(anchura)+".png"))
        logo.set_from_pixbuf(image)
        relabel(next,k*28,True)
        relabel(more,k*25,True)
        #relabel(listl,k*25,True)
        relabel(title,k*33,True)
        relabel2(eventl,k*28,True)


        for name  in ["recbutton","pausebutton","stopbutton","helpbutton", ]:
            button = self.gui.get_object(name) #100, 80
            button.set_property("width-request", int(k*100) )
            button.set_property("height-request", int(k*100) )

            image = button.get_children()
            if type(image[0]) == gtk.Image:
                image[0].set_pixel_size(int(k*80))            
            else:
                relabel(image[0],k*28,False)

        for name  in ["previousbutton"]:
            button = self.gui.get_object(name)
            button.set_property("width-request", int(k*70) )
            button.set_property("height-request", int(k*70) )

            image = button.get_children()
            if type(image[0]) == gtk.Image:
                image[0].set_pixel_size(int(k*56))  
                image[0].set_padding(int(k*50),0)


        button = self.gui.get_object("top_align")
        button.set_padding(int(k*20),int(k*40),int(k*50),int(k*50))
        button = self.gui.get_object("control_align")
        button.set_padding(int(k*10),int(k*30),int(k*50),int(k*50))
        #button = self.gui.get_object("alignment2")
        #button.set_padding(int(k*10),int(k*20),int(k*50),int(k*50))
        button = self.gui.get_object("vubox")
        button.set_padding(int(k*20),int(k*10),int(k*40),int(k*40)) 

        align2r.set_padding(int(k*10),int(k*30),int(k*120),int(k*120))
        pbox.set_property("width-request", int(k*225) )


       
        return True
        
    def change_state(self, state): # TODO empequenecer esta funcion
        record = self.gui.get_object("recbutton")
        pause = self.gui.get_object("pausebutton")
        stop = self.gui.get_object("stopbutton")
        #test = self.gui.get_object("testbutton")
        helpb = self.gui.get_object("helpbutton")
        editb = self.gui.get_object("editbutton")
        status = self.gui.get_object("bigstatus")
        #status2 = self.gui.get_object("bigstatus2")
        bgstatus = self.gui.get_object("bg_status")
        prevb = self.gui.get_object("previousbutton")
  
        if state != self.status: # only change if it is not a status reload
            self.previous,self.status = self.status,state

        if state != GC_RECORDING:
            if self.normal_style != None:
                bgstatus.set_style(self.normal_style)

        if state == GC_INIT:
            record.set_sensitive(False)
            pause.set_sensitive(False)
            stop.set_sensitive(False)
            #test.set_sensitive(False) #TODO make a test or take out the button
            helpb.set_sensitive(True) #TODO a help pop-up
            prevb.set_sensitive(True)
            editb.set_sensitive(False)
            self.dispatcher.emit("update-rec-status", "Initialization")

            

        elif state == GC_PREVIEW:    
            record.set_sensitive( (self.allow_start or self.allow_manual) ) # IDEA set a timer to allow the presenter to move to his-her position
            pause.set_sensitive(False)
            pause.set_active(False)
            stop.set_sensitive(False)
            #test.set_sensitive(False)
            helpb.set_sensitive(True)
            prevb.set_sensitive(True)
            editb.set_sensitive(False)
            if self.next == None:
                self.dispatcher.emit("update-rec-status", "Idle")            
            else:
                self.dispatcher.emit("update-rec-status", "Waiting")            

        elif state == GC_RECORDING:
            record.set_sensitive(False)
            pause.set_sensitive(False) # SHOULD BE self.allow_pause, False to disable pause
            stop.set_sensitive( (self.allow_stop or self.allow_manual) )
            #test.set_sensitive(False)
            helpb.set_sensitive(True)
            prevb.set_sensitive(False)
            editb.set_sensitive(True)    
            if bgstatus.get_style().bg[gtk.STATE_NORMAL] != gtk.gdk.color_parse('red'):
                self.normal_style = bgstatus.get_style().copy()
                cambio=bgstatus.get_style().copy()
                cambio.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse('red')
                #cambio.font_desc =
                bgstatus.set_style(cambio)
            else:
                log.info("Already RED")
            self.dispatcher.emit("update-rec-status", "  Recording  ")

        elif state == GC_PAUSED:
            record.set_sensitive(False)
            pause.set_sensitive(False) # The pause would be on a popup
            stop.set_sensitive(False)
            prevb.set_sensitive(False)
            #stop.set_sensitive((self.allow_stop or self.allow_manual) )
            helpb.set_sensitive(False)
            editb.set_sensitive(True)
  
            self.dispatcher.emit("update-rec-status", "Paused")
            
        elif state == GC_STOP:
            if self.previous == GC_PAUSED:
                self.pause_dialog.destroy()
            record.set_sensitive(False)
            pause.set_sensitive(False)
            stop.set_sensitive(False)
            helpb.set_sensitive(True)
            prevb.set_sensitive(True)
            editb.set_sensitive(False)
            self.dispatcher.emit("update-rec-status", "Stopped")
            self.warning_audio_destroy(None)
            

        elif state == GC_BLOCKED: # FIXME not necessary
            record.set_sensitive(False)
            pause.set_sensitive(False)
            stop.set_sensitive(False)
            helpb.set_sensitive(False)   
            prevb.set_sensitive(False)
            editb.set_sensitive(False)

        status.set_text(self.statusbar.GetStatus())
        #status2.set_text(self.statusbar.GetStatus())

    def block(self):
        prev = self.gui.get_object("prebox")
        prev.set_child_visible(False)
        self.focus_is_active = True
        self.event_change_mode(None, 3, 0)

        # SHOW HELP OR EDIT_META
        helpbutton = self.gui.get_object("helpbutton")
        helpbutton.set_visible(True)
        editbutton = self.gui.get_object("editbutton")
        #editbutton.set_no_show_all(True)
        editbutton.set_visible(False)

 
    def close(self, signal):
        if self.status in [GC_RECORDING]:
            self.close_recording() 
        #self.timer_thread_id = None
        self.scheduler_thread_id = None
        self.clock_thread_id = None
        self.start_thread_id = None
        if self.status in [GC_PREVIEW]:
            self.record.stop_preview()
        
        return True        


gobject.type_register(RecorderClassUI)
