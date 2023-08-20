from datetime import datetime
from django import template
from django.utils.safestring import mark_safe

from mudur.models import ApprovalDate
from mudur.settings import REQUIRE_TRAINESS_APPROVE
from training.models import TrainessCourseRecord
from userprofile.models import TrainessClassicTestAnswers, TrainessNote, UserProfileBySite
from userprofile.userprofileops import UserProfileOPS
from training.tutils import getparticipationforms, getparticipationforms_by_date

register = template.Library()


@register.simple_tag(name="mod")
def mod(num):
    return -num


@register.simple_tag(name="isdategtnow_head")
def isdategtnow_head(datedict, key):
    now = datetime.now()
    adate = datedict.get(key)
    if adate:
        if adate.end_date >= now >= adate.start_date:
            return "Onayla"
    if REQUIRE_TRAINESS_APPROVE:
        return "Geleceğini Teyid Etti"
    return "Onaylandı"


@register.simple_tag(name="manuallyaddtrainess")
def manuallyaddtrainess(site, user):
    now = datetime.date(datetime.now())
    if site.event_start_date > now > site.application_end_date and user.is_staff:
        return mark_safe("""
        <div class="alert alert-info">Sistemde profili tanimli olup başvuruyu kaçırmış kullanıcıları "Kursiyer Ekle"
         butonuna tıklayarak kursunuza ekleyebilirsiniz</div>
        <a href="/egitim/katilimciekle" class="btn btn-primary pull-right" type="button" data-toggle="modal"><i class="fa fa-fw fa-plus"></i>
        Kursiyer Ekle
      </a>""")
    return ""


@register.simple_tag(name="authorizedforelection", takes_context=True)
def authorizedforelection(context, site, user, course):
    now = datetime.date(datetime.now())
    approvaldates = ApprovalDate.objects.filter(for_instructor=True, site=context['request'].site).order_by("start_date")
    if approvaldates:
        if site.event_start_date > now and approvaldates[0].start_date <= datetime.now() <= approvaldates[
            0].end_date and UserProfileOPS.is_authorized_inst(user.userprofile, course=course):
            return mark_safe("""
            <div class="alert alert-danger">
                Uyarı: <p>* Onay tarihleri içerisinde kabul e-postaları onayladığınız 1. tercihi kursunuz olan katılımcılara gönderilir.</p>
                       <p>* Kabul e-postası gönderilen kullanıcıların onayını kaldıramazsınız!</p>
                       <p>* Onaylanan diğer (1. tercihi kursunuz olmayan) katılımcıların kabul e-postaları onay tarihi bitiminde gönderilir.</p>
                       <p>* El ile eklediğiniz katılımcıları 1. tercih listesinde görüntüleyebilirsiniz.</p>
            </div>
            <button type="submit" class="btn btn-success pull-left" name="send">Gönder</button>
            """)
    return ""


@register.filter
def subtract(value, arg):
    return value - arg

@register.simple_tag(name="isdategtnow_body", takes_context=True)
def isdategtnow_body(context, datedict, key, t, course, user):
    now = datetime.now()
    adate = datedict.get(key)
    if adate:
        if adate.end_date >= now >= adate.start_date and UserProfileOPS.is_authorized_inst(
                user.userprofile, course=course) and not t.consentemailsent:
            approvedprefs = TrainessCourseRecord.objects.filter(trainess=t.trainess,
                                                                course__site=context['request'].site,
                                                                approved=True)
            is_selectable = True
            priviliged_pref = None

            for approvedpref in approvedprefs:
                if approvedpref.consentemailsent:
                    is_selectable = False
                    priviliged_pref = approvedpref
                elif t.preference_order > approvedpref.preference_order:
                    is_selectable = False
                    priviliged_pref = approvedpref

            if t.trainess.useraccomodationpref_set.exists():
                trainess_accomodation = t.trainess.useraccomodationpref_set.first()
                acc_is_full = trainess_accomodation.accomodation.is_full
            else:
                acc_is_full = False
            if is_selectable:
                dom = "<div>"
                if t.approved:
                    dom += "<input type=\"checkbox\" checked name=\"students%s\" value=\"%s\"/>" % (course.id, t.pk)
                elif acc_is_full:
                    dom += "<input type=\"checkbox\" name=\"students%s\" value=\"%s\"/ title=\"%s kontenjani doldu\" disabled>" % (course.id, t.pk,trainess_accomodation.accomodation.name)
                else:
                    dom += "<input type=\"checkbox\" name=\"students%s\" value=\"%s\"/>" % (course.id, t.pk)
                dom += "</div>"
                return mark_safe(dom)
            else:
                return "%d. tercihi kabul edilmis." % priviliged_pref.preference_order
    if (t.trainess_approved and REQUIRE_TRAINESS_APPROVE) or (t.approved and not REQUIRE_TRAINESS_APPROVE):
        return "Evet"
    else:
        return "Hayir"

@register.simple_tag(name="getconsentmailfield")
def getconsentmailfield(tcr, user):
    consentemailsentt = TrainessCourseRecord.objects.filter(trainess=tcr.trainess, course__site__is_active=True, consentemailsent=True).first()
    if tcr.consentemailsent:
        return "Gönderildi"
    elif consentemailsentt and  consentemailsentt != tcr:
        return "%s. tercihi icin gonderildi" % str(consentemailsentt.preference_order)
    elif not tcr.consentemailsent and tcr.preference_order == 1 and UserProfileOPS.is_authorized_inst(user.userprofile, course=tcr.course):
        now = datetime.date(datetime.now())
        approvaldates = ApprovalDate.objects.filter(site=tcr.course.site).order_by("start_date")
        if approvaldates:
            if tcr.course.site.event_start_date > now and approvaldates[0].start_date <= datetime.now() <= approvaldates[
                0].end_date:
                dom = "<div>"
                if tcr.trainess.useraccomodationpref_set.exists():
                    trainess_accomodation = tcr.trainess.useraccomodationpref_set.first()
                    acc_is_full = trainess_accomodation.accomodation.is_full
                else:
                    acc_is_full = False
                if acc_is_full:
                    dom += "<input type=\"checkbox\" name=\"consentmail%s\" value=\"%s\"/ title=\"%s kontenjani doldu\" disabled>" % (tcr.course.pk, tcr.pk,trainess_accomodation.accomodation.name)
                else:
                    dom += "<input type=\"checkbox\" name=\"consentmail%s\" value=\"%s\"/>" % (tcr.course.pk, tcr.pk)
                dom += "</div>"
                return mark_safe(dom)
        return "Gonderilmedi"
    else:
        return "Gönderilmedi"


@register.simple_tag(name="getanswer")
def getanswer(question, user):
    try:
        return TrainessClassicTestAnswers.objects.get(question=question, user=user.userprofile).answer
    except TrainessClassicTestAnswers.DoesNotExist:
        return ""


@register.simple_tag(name="gettrainesscolor", takes_context=True)
def gettrainesscolor(context, trainess, courserecord):
    if courserecord.trainess_approved:
        return mark_safe("<div class =\"approved-trainess-for-this-course\" ></div >")
    elif courserecord.approved:
        return mark_safe("<div class =\"checked-trainee-course\" ></div>")
    else:
        is_approved_another_course = TrainessCourseRecord.objects.filter(course__site=context['request'].site,
                                                                         trainess=trainess, approved=True)
        if is_approved_another_course:
            return mark_safe("<div class =\"checked-for-another-course\" > </div>")
    return ""


@register.simple_tag(name="getapprovedcourse", takes_context=True)
def gettrainessapprovedpref(context, courserecord):
    trainess_approved_prefs = TrainessCourseRecord.objects.filter(course__site=context['request'].site,
                                                                  trainess=courserecord.trainess,
                                                                  approved=True).exclude(
        pk=courserecord.pk)
    html = ""
    for tap in trainess_approved_prefs:
        html += "<div class =\"checked-for-another-course\" > Kursiyer %s.tercihi olan %s kursuna kabul edilmiş </br>" \
                "</div>" % (tap.preference_order, tap.course.name)
    return mark_safe(html)


@register.simple_tag(name="getallprefs", takes_context=True)
def getallprefs(context, courserecord):
    trainess_all_prefs = TrainessCourseRecord.objects.filter(course__site=context['request'].site,
                                                             trainess=courserecord.trainess).exclude(
        pk=courserecord.pk)
    html = ""
    for pref in trainess_all_prefs:
        html += "<div> %s.tercihi - %s (%s) </br></div>" % (pref.preference_order, pref.course.name, pref.course.no)
    return mark_safe(html)



@register.simple_tag(name="getparticipationheader")
def getparticipationheader(site):
    html = ""
    for date in range(1, int((site.event_end_date - site.event_start_date).days) + 2):
        html += "<th>%s. gun</th>" % str(date)
    return mark_safe(html)

@register.simple_tag(name="getapprovedtrainess")
def getapprovedtrainess(course):
    
    tcrs = TrainessCourseRecord.objects.filter(course=course,approved=True)
    html = ""
    for tcr in tcrs:
        html += "<tr><th>%s</th><th>%s</th><th>%s</th><th></th><th></th></tr>" % (str(tcr.pk),tcr.trainess.user.first_name,tcr.trainess.user.last_name)
    return mark_safe(html)

@register.simple_tag(name="getparforms")
def getparforms(site, cr):
    html = ""
    forms = getparticipationforms(site, cr)
    for form in forms:
        html += "<td>" + form.as_p() + "</td>"
    return mark_safe(html)


@register.simple_tag(name="getparformsbydate")
def getparformsbydate(cr, date):
    form = getparticipationforms_by_date(cr, date)
    return mark_safe(form.as_ul())


@register.simple_tag(name="usernotesaddedbyinst")
def usernotesaddedbyinst(ruser, tuser):
    trainessnotes = TrainessNote.objects.filter(note_from_profile=ruser.userprofile, note_to_profile=tuser)
    html = "<h3>Eklediğiniz Notlar</h3>"
    if trainessnotes:
        for trainessnote in trainessnotes:
            html += """
            <section>
                <p> %s - %s</p>
                <ul>
                    <li> <b>Not:</b><p>%s</p></li>
                    <li> <b>Tarih:</b><p>%s</p></li>
                </ul>
            </section>
            """ % (trainessnote.site.name, trainessnote.site.year, trainessnote.note,
                   trainessnote.note_date.strftime('%d-%m-%Y'))
    else:
        html = "Not Yok."
    return mark_safe(html)


@register.simple_tag(name="potentialinstform")
def potentialinstform(tuser):
    html = "<label for='potential-%s'> Potansiyel Eğitmen </label>" % tuser.pk
    try:
        tuserprofilebysite = UserProfileBySite.objects.get(user=tuser, site__is_active=True)
        if tuserprofilebysite.potentialinstructor:
            html += "<input type = 'checkbox' id='potential-%s' name='potential-%s' checked />" % (tuser.pk, tuser.pk)
        else:
            html += "<input type='checkbox' id='potential-%s' name='potential-%s' />" % (tuser.pk, tuser.pk)
        return mark_safe(html)
    except UserProfileBySite.DoesNotExist:
        html += "<input type='checkbox' id='potential-%s' name='potential-%s' />" % (tuser.pk, tuser.pk)
        return mark_safe(html)
