#!/usr/bin/env python3
"""Write data/videos.json entries + quizzes for 3 LevelUpRN pharmacology videos.

Content is authored from the transcripts (scratch/tr_*.json) following
skills/nclex-quiz-builder. Every `ts` is the exact second the fact is stated
in that video — no guesswork. Chapters come from the real YouTube marks.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCR = '/Users/matin/.hermes/profiles/brain-hub/cache/scratch'
GEN = '2026-10-19'
meta = json.load(open(SCR + '/meta3.json', encoding='utf-8'))

CAT_FA, CAT_EN = 'فارماکولوژی', 'Pharmacology'

VIDEOS = {
    'gYajexY55hM': {
        'fa': 'آمیودارون: ضدآریتمی کلاس سه — مکانیسم، عوارض و هشدارهای بلک‌باکس',
        'en': 'Amiodarone (Class III Antiarrhythmic): Mechanism, Side Effects & Black Box Warnings',
        'sum': 'آمیودارون، ضدآریتمی کلاس سه برای آریتمی‌های تهدیدکنندهٔ حیات مثل فیبریلاسیون و تاکی‌کاردی بطنی. مکانیسم آن با بلوکه کردن کانال پتاسیم و طولانی کردن پتانسیل عمل قلبی است. عوارض مهم شامل افت فشار، برادی‌کاردی، اختلال بینایی، اختلال تیروئید، حساسیت به نور و تغییر رنگ آبی‌ـ‌خاکستری پوست است. سه هشدار بلک‌باکس دارد: سمیت ریوی، کبدی و قلبی. پایش شامل نوار قلب، الکترولیت‌ها، عملکرد ریه و کبد (AST/ALT) و تیروئید (T3، T4، TSH) است. آموزش بیمار: پرهیز از آب گریپ‌فروت، معاینۀ منظم چشم و ضدآفتاب.',
        'sum_en': 'Amiodarone is a Class III antiarrhythmic for life-threatening arrhythmias such as VF and VT. It blocks potassium channels, prolonging the action potential. Key adverse effects include hypotension, bradycardia, visual changes, thyroid dysfunction, photosensitivity and blue-gray skin discoloration. It carries three black box warnings — pulmonary, hepatic and cardiac toxicity. Monitoring covers ECG, electrolytes, lung function, AST/ALT and T3/T4/TSH. Patient teaching includes avoiding grapefruit juice, regular eye exams and sun protection.',
        'ch': [['۰:۰۰', 'مقدمه'], ['۰:۳۲', 'موارد مصرف'], ['۱:۰۱', 'مکانیسم اثر'],
               ['۱:۲۳', 'عوارض جانبی'], ['۲:۴۴', 'آموزش به بیمار'], ['۳:۲۱', 'آزمون']],
        'ch_en': [['0:00', 'Intro'], ['0:32', 'Indications'], ['1:01', 'Mode of Action'],
                  ['1:23', 'Side Effects'], ['2:44', 'Patient Teaching'], ['3:21', 'Quiz Time']],
    },
    'gHASyDK8Hfo': {
        'fa': 'بلوکرهای کانال سدیم (پروکاین‌آمید، لیدوکاین و فلکاینید): ضدآریتمی‌های کلاس یک',
        'en': 'Sodium Channel Blockers (Procainamide, Lidocaine & Flecainide): Class I Antiarrhythmics',
        'sum': 'بلوکرهای کانال سدیم، ضدآریتمی‌های کلاس یک هستند که در سه زیرگروه 1A، 1B و 1C دسته‌بندی می‌شوند؛ پروکاین‌آمید در 1A، لیدوکاین در 1B و فلکاینید در 1C قرار دارند. با بلوکه کردن کانال سدیم و کاهش ورود سدیم به سلول، ضربان قلب کند می‌شود. برای آریتمی‌های بطنی و تاکی‌کاردی فوق‌بطنی مانند سندرم ولف–پارکینسون–وایت استفاده می‌شوند. عوارض شامل سرگیجه، برادی‌کاردی، افت فشار و آریتمی است و هشدار بلک‌باکس دارند. پروکاین‌آمید می‌تواند باعث دیسکرازی خونی و سندرم شبه‌لوپوس شود. پایش: نوار قلب، علائم حیاتی، سطح سرمی دارو (۴ تا ۱۰ میکروگرم در میلی‌لیتر) و CBC.',
        'sum_en': 'Sodium channel blockers are Class I antiarrhythmics split into 1A, 1B and 1C: procainamide (1A), lidocaine (1B) and flecainide (1C). They block sodium channels, reducing sodium influx and slowing impulses. Used for ventricular arrhythmias and supraventricular tachycardia such as Wolff-Parkinson-White. Adverse effects include dizziness, bradycardia, hypotension and arrhythmias, with black box warnings. Procainamide additionally causes blood dyscrasias and a lupus-like syndrome. Monitoring includes ECG, vital signs, serum drug levels (4-10 mcg/mL) and CBC.',
        'ch': [['۰:۰۰', 'مقدمه'], ['۰:۵۷', 'موارد مصرف'], ['۱:۱۳', 'مکانیسم اثر'],
               ['۱:۳۱', 'عوارض جانبی'], ['۲:۱۱', 'مراقبت پرستاری'], ['۲:۵۰', 'آزمون']],
        'ch_en': [['0:00', 'Intro'], ['0:57', 'Indications'], ['1:13', 'Mode of Action'],
                  ['1:31', 'Side Effects'], ['2:11', 'Nursing Care'], ['2:50', 'Quiz Time']],
    },
    'Z1CF4pWvsj0': {
        'fa': 'دیگوکسین (گلیکوزید قلبی): اثر اینوتروپیک مثبت، سمیت و پایش',
        'en': 'Digoxin (Cardiac Glycoside): Positive Inotropic Effect, Toxicity & Monitoring',
        'sum': 'دیگوکسین یک گلیکوزید قلبی است که برای نارسایی قلبی، فیبریلاسیون دهلیزی و فلوتر دهلیزی به‌کار می‌رود. اثر اینوتروپیک مثبت دارد یعنی قدرت انقباض قلب را افزایش می‌دهد و اثر کرونوتروپیک منفی یعنی ضربان قلب را کند می‌کند. سمیت دیگوکسین با تهوع و استفراغ، خستگی، ضعف، سرگیجه و تغییرات بینایی مثل تاری دید یا دیدن هاله‌های سبز و زرد بروز می‌کند. مهم‌ترین نکتهٔ پرستاری: پیش از تجویز باید نبض بیمار بررسی شود و اگر کمتر از ۶۰ بار در دقیقه بود دارو داده نشود. سطح درمانی سرم ۰٫۵ تا ۲ نانوگرم در میلی‌لیتر است و هیپوکالمی خطر سمیت را افزایش می‌دهد. پادزهر، دیگوکسین ایمون فاب است.',
        'sum_en': 'Digoxin is a cardiac glycoside used for heart failure, atrial fibrillation and atrial flutter. It has a positive inotropic effect (stronger contractions) and a negative chronotropic effect (slower rate). Toxicity presents with nausea, vomiting, fatigue, weakness, dizziness and visual changes such as blurred vision or green-yellow halos. Key nursing step: check the pulse before administration and withhold the dose if the rate is under 60 beats per minute. Therapeutic serum range is 0.5-2 ng/mL; hypokalemia increases toxicity risk. The antidote is digoxin immune Fab.',
        'ch': [['۰:۰۰', 'مقدمه'], ['۰:۳۸', 'موارد مصرف و مکانیسم اثر'], ['۱:۱۸', 'عوارض جانبی'],
               ['۱:۴۷', 'مراقبت پرستاری'], ['۲:۴۴', 'آزمون']],
        'ch_en': [['0:00', 'Intro'], ['0:38', 'Indications & Mode of Action'],
                  ['1:18', 'Side Effects'], ['1:47', 'Nursing Care'], ['2:44', 'Quiz Time']],
    },
}

QUIZZES = {
    # ---------------------------------------------- amiodarone
    'gYajexY55hM': {'video': 'gYajexY55hM', 'gen': GEN, 'questions': [
        {'type': 'mc', 'ts': 138,
         'qf': 'بیماری که آمیودارون دریافت می‌کند دچار نوسان سطح پتاسیم شده است. پرستار باید نخستین چیزی که باید بررسی کند چیست؟',
         'qe': 'A client receiving amiodarone has fluctuating potassium levels. What should the nurse assess first?',
         'of': ['نوار قلب، برای شناسایی آریتمی جدید یا تشدیدشده',
               'رنگ پوست بیمار، برای تشخیص تغییر آبی‌ـ‌خاکستری',
               'نتایج آزمایش تیروئید، برای بررسی کم‌کاری تیروئید',
               'دید بیمار، برای بررسی تغییرات بینایی'],
         'oe': ['The ECG, to identify new or worsening arrhythmias',
               'The skin color, to detect blue-gray discoloration',
               'Thyroid test results, to check for hypothyroidism',
               'The client’s vision, to assess visual changes'],
         'c': 0,
         'wf': 'آمیودارون کانال پتاسیم را بلوکه می‌کند و اثر دارو با سطح پتاسیم تنظیم می‌شود؛ نوسان پتاسیم می‌تواند آریتمی‌های خطرناک ایجاد کند. به همین دلیل ویدیو پایش نوار قلب و الکترولیت‌ها را در اولویت اول قرار می‌دهد. تغییر رنگ پوست، بینایی و تیروئید همگی عوارض واقعی دارند اما فوریت آریتمی را ندارند.',
         'we': 'Amiodarone blocks potassium channels, so its effect tracks the potassium level, and potassium shifts can trigger dangerous arrhythmias. That is why the video puts ECG and electrolyte monitoring first. Blue-gray skin, visual changes and thyroid dysfunction are all real adverse effects, but none is as time-critical as an arrhythmia.'},

        {'type': 'mc', 'ts': 173,
         'qf': 'پرستار باید بیماری را که آمیودارون مصرف می‌کند دربارهٔ نوشیدن آب گریپ‌فروت آموزش دهد. دلیل اصلی این آموزش چیست؟',
         'qe': 'The nurse should teach a client taking amiodarone about grapefruit juice. What is the main reason?',
         'of': ['آب گریپ‌فروت اثر دارو را کاهش می‌دهد و کنترل آریتمی از دست می‌رود',
               'آب گریپ‌فروت سطح دارو را در بدن افزایش می‌دهد و خطر سمیت ایجاد می‌کند',
               'آب گریپ‌فروت باعث تغییر رنگ پوست به آبی‌ـ‌خاکستری می‌شود',
               'آب گریپ‌فروت با تیروکسین تداخل دارد و کم‌کاری تیروئید ایجاد می‌کند'],
         'oe': ['Grapefruit juice decreases the effect of the drug and control of the arrhythmia is lost',
               'Grapefruit juice raises the drug level in the body and creates a risk of toxicity',
               'Grapefruit juice causes the blue-gray skin discoloration',
               'Grapefruit juice interacts with thyroxine and causes hypothyroidism'],
         'c': 1,
         'wf': 'ویدیو تصریح می‌کند که گریپ‌فروت سطح آمیودارون را در بدن بالا می‌برد و ممکن است به سمیت برسد. تغییر رنگ پوست و اختلال تیروئید عوارض مستقل دارو هستند و ربطی به گریپ‌فروت ندارند.',
         'we': 'The video states that grapefruit raises amiodarone levels in the body and can lead to toxicity. The blue-gray skin and thyroid dysfunction are independent drug adverse effects with no link to grapefruit.'},

        {'type': 'cloze', 'ts': 63,
         'qf': 'آمیودارون با بلوکه کردن کانال {0} در سلول عضلهٔ قلبی، پتانسیل عمل را طولانی کرده و رپلاریزاسیون را به تأخیر می‌اندازد.',
         'qe': 'Amiodarone blocks the {0} channels in cardiac muscle cells, prolonging the action potential and delaying repolarization.',
         'blanks': ['پتاسیم', 'potassium'],
         'wf': 'ضدآریتمی‌های کلاس سه کانال پتاسیم را بلوکه می‌کنند. کاهش خروج پتاسیون، پتانسیل عمل را طولانی کرده و تحریک‌پذیری سلول قلبی را کاهش می‌دهد تا ریتم‌های نابهنجار تثبیت شوند.',
         'we': 'Class III antiarrhythmics block potassium channels. Reduced potassium outflow prolongs the action potential and lowers cardiac cell excitability, stabilizing abnormal rhythms.'},

        {'type': 'cloze', 'ts': 110,
         'qf': 'یکی از سه هشدار بلک‌باکس آمیودارون، سمیت {0} است که می‌تواند به التهاب شدید ریه منجر شود.',
         'qe': 'One of amiodarone’s three black box warnings is {0} toxicity, which can lead to severe lung inflammation.',
         'blanks': ['ریوی', 'pulmonary'],
         'wf': 'سه هشدار بلک‌باکس آمیودارون عبارت‌اند از سمیت ریوی، سمیت کبدی و سمیت قلبی. سمیت قلبی می‌تواند آریتمی‌هایی مانند تورسادس‌دوپوینت ایجاد کند و سمیت کبدی آنزیم‌های کبدی را بالا می‌برد.',
         'we': 'Amiodarone carries three black box warnings: pulmonary, hepatic and cardiac toxicity. Cardiac toxicity can cause arrhythmias such as torsades de pointes, and hepatic toxicity raises liver enzymes.'},

        {'type': 'dnd', 'ts': 138,
         'qf': 'پایش‌های لازم در طول درمان با آمیودارون را به همان ترتیبی بچینید که در ویدیو بیان می‌شود.',
         'qe': 'Arrange the required monitoring for a client on amiodarone in the order the video states.',
         'items': ['پایش عملکرد تیروئید با T3، T4 و TSH',
                   'پایش عملکرد ریه با تست عملکرد ریه و اسکن قفسه سینه',
                   'پایش نوار قلب، علائم حیاتی و الکترولیت‌ها',
                   'پایش عملکرد کبد با AST و ALT'],
         'keep': ['پایش نوار قلب، علائم حیاتی و الکترولیت‌ها',
                  'پایش عملکرد ریه با تست عملکرد ریه و اسکن قفسه سینه',
                  'پایش عملکرد کبد با AST و ALT',
                  'پایش عملکرد تیروئید با T3، T4 و TSH'],
         'wf': 'ویدیو ترتیب پایش را چنین بیان می‌کند: نخست نوار قلب و علائم حیاتی و الک trolیت‌ها، سپس عملکرد ریه، سپس عملکرد کبد با AST و ALT و در پایان عملکرد تیروئید با T3، T4 و TSH.',
         'we': 'The video gives the monitoring order: ECG and vital signs and electrolytes first, then lung function, then liver function with AST and ALT, and thyroid function with T3, T4 and TSH last.'},
    ]},

    # ---------------------------------------------- sodium channel blockers
    'gHASyDK8Hfo': {'video': 'gHASyDK8Hfo', 'gen': GEN, 'questions': [
        {'type': 'mc', 'ts': 113,
         'qf': 'بیماری که پروکاین‌آمید دریافت می‌کند برای درد مفاصل و تب مراجعه کرده است. پرستار باید در نظر بگیرد که این علائم چه معنایی دارند؟',
         'qe': 'A client receiving procainamide reports joint pain and fever. What should the nurse recognize about these symptoms?',
         'of': ['نشانهٔ دیسکرازی خونی است و نیاز به پایش فوری CBC دارد',
               'عارضهٔ شایع این گروه دارویی است و با قطع دارو برطرف می‌شود',
               'نشانهٔ سندرم شبه‌لوپوس است که ممکن است با پروکاین‌آمید رخ دهد',
               'نشانهٔ واکنش آلرژیک به کمک‌حامل است و نیاز به آنتی‌هیستامین دارد'],
         'oe': ['They indicate a blood dyscrasia and require immediate CBC monitoring',
               'They are a common effect of this drug class and resolve when the drug is stopped',
               'They indicate a lupus-like syndrome that can occur with procainamide',
               'They indicate an allergic reaction to the vehicle and require an antihistamine'],
         'c': 2,
         'wf': 'ویدیو به‌صراحت می‌گوید پروکاین‌آمید می‌تواند سندرم شبه‌لوپوس با علائمی مانند درد مفاصل و تب ایجاد کند. دیسکرازی خونی پروکاین‌آمید نیز هست، اما با کاهش شمارش پلاکت و گلبول سفید خود را نشان می‌دهد، نه با درد مفاصل.',
         'we': 'The video states that procainamide can cause a lupus-like syndrome with symptoms such as joint pain and fever. Procainamide also causes blood dyscrasias, but those present as low platelet and white cell counts rather than joint pain.'},

        {'type': 'mc', 'ts': 157,
         'qf': 'کدام بازه، سطح سرمی درمانی پروکاین‌آمید است؟',
         'qe': 'Which range is the therapeutic serum level for procainamide?',
         'of': ['۰٫۵ تا ۲ نانوگرم در میلی‌لیتر',
               '۴ تا ۱۰ میکروگرم در میلی‌لیتر',
               '۱۰ تا ۲۰ میکروگرم در میلی‌لیتر',
               '۲ تا ۵ میکروگرم در میلی‌لیتر'],
         'oe': ['0.5 to 2 ng/mL', '4 to 10 mcg/mL', '10 to 20 mcg/mL', '2 to 5 mcg/mL'],
         'c': 1,
         'wf': 'ویدیو صریحاً بازهٔ درمانی پروکاین‌آمید را بین ۴ تا ۱۰ میکروگرم در میلی‌لیتر ذکر می‌کند. بازهٔ ۰٫۵ تا ۲ نانوگرم در میلی‌لیتر متعلق به دیگوکسین است و به‌عنوان گزینهٔ انحرافی آمده است.',
         'we': 'The video gives the therapeutic range for procainamide as 4 to 10 mcg/mL. The 0.5 to 2 ng/mL range belongs to digoxin and serves as the distractor here.'},

        {'type': 'cloze', 'ts': 76,
         'qf': 'بلوکرهای کانال سدیم با بلوکه کردن کانال {0} در سلول عضلهٔ قلبی، ورود سدیم به سلول را کاهش می‌دهند و ضربان قلب را کند می‌کنند.',
         'qe': 'Sodium channel blockers block the {0} channels in cardiac muscle cells, reducing sodium influx and slowing the heart rate.',
         'blanks': ['سدیم', 'sodium'],
         'wf': 'این داروها ضدآریتمی کلاس یک هستند. با کاهش سدیم ورودی، تحریک‌پذیری سلول کم می‌شود و ضربان سریع و آشفتهٔ آریتمی متوقف می‌گردد.',
         'we': 'These are Class I antiarrhythmics. Reduced sodium entry lowers cell excitability and stops the fast, chaotic impulses of an arrhythmia.'},

        {'type': 'cloze', 'ts': 42,
         'qf': 'پروکاین‌آمید در زیرگروه {0} ، لیدوکاین در 1B و فلکاینید در 1C دسته‌بندی می‌شوند.',
         'qe': 'Procainamide is classified in subgroup {0}, lidocaine in 1B and flecainide in 1C.',
         'blanks': ['1A', '1A'],
         'wf': 'ضدآریتمی‌های کلاس یک به سه زیرگروه تقسیم می‌شوند: پروکاین‌آمید در 1A، لیدوکاین در 1B و فلکاینید در 1C. این دسته‌بندی از نکات پرتکرار آزمون پرستاری است.',
         'we': 'Class I antiarrhythmics split into three subgroups: procainamide in 1A, lidocaine in 1B and flecainide in 1C. This is a frequently tested nursing-school classification.'},

        {'type': 'dnd', 'ts': 134,
         'qf': 'اقدامات پایش برای بیماری که پروکاین‌آمید دریافت می‌کند را به همان ترتیبی بچینید که در ویدیو بیان می‌شود.',
         'qe': 'Arrange the monitoring actions for a client receiving procainamide in the order the video states.',
         'items': ['پایش CBC، به‌دلیل خطر دیسکرازی خونی',
                   'پایش نوار قلب برای آریتمی جدید یا تشدیدشده',
                   'پایش سطح سرمی دارو در طول درمان',
                   'پایش دقیق علائم حیاتی، چون افت فشار و برادی‌کاردی عوارض کلیدی هستند'],
         'keep': ['پایش نوار قلب برای آریتمی جدید یا تشدیدشده',
                  'پایش دقیق علائم حیاتی، چون افت فشار و برادی‌کاردی عوارض کلیدی هستند',
                  'پایش سطح سرمی دارو در طول درمان',
                  'پایش CBC، به‌دلیل خطر دیسکرازی خونی'],
         'wf': 'ویدیو ترتیب مراقبت را چنین بیان می‌کند: نخست نوار قلب، سپس علائم حیاتی، سپس سطح سرمی دارو و در پایان CBC به‌دلیل خطر دیسکرازی خونی.',
         'we': 'The video gives the nursing-care order: ECG first, then vital signs, then serum drug levels, and CBC last because of the risk of blood dyscrasias.'},
    ]},

    # ---------------------------------------------- digoxin
    'Z1CF4pWvsj0': {'video': 'Z1CF4pWvsj0', 'gen': GEN, 'questions': [
        {'type': 'mc', 'ts': 114,
         'qf': 'پیش از تجویز دیگوکسین، پرستار نبض بیمار را بررسی می‌کند. اگر نبض بیمار ۵۰ بار در دقیقه باشد، مناسب‌ترین اقدام کدام است؟',
         'qe': 'Before administering digoxin, a nurse assesses the client’s pulse. If the pulse is 50 beats per minute, what is the most appropriate action?',
         'of': ['تجویز دارو، زیرا اثر کرونوتروپیک منفی به کنترل آریتمی کمک می‌کند',
               'تجویز نکردن دارو و اطلاع‌دادن به پزشک، زیرا نبض کمتر از ۶۰ است',
               'تجویز نصف دوز به‌دلیل خطر افت فشار خون',
               'تجویز دارو و پایش سطح سرمی پس از شش ساعت'],
         'oe': ['Administer the drug, because its negative chronotropic effect helps control the arrhythmia',
               'Withhold the dose and notify the provider, because the pulse is under 60',
               'Administer half the dose because of hypotension risk',
               'Administer the drug and monitor the serum level after six hours'],
         'c': 1,
         'wf': 'قانون کلیدی این ویدیو این است که اگر نبض بیمار کمتر از ۶۰ بار در دقیقه باشد، دیگوکسین داده نمی‌شود. برادی‌کاردی یکی از عوارض این داروست و دوز دادن در این وضعیت خطر سمیت را بالا می‌برد.',
         'we': 'The key rule in this video is that digoxin is withheld when the pulse is under 60 beats per minute. Bradycardia is an adverse effect of the drug, and giving the dose in that state raises toxicity risk.'},

        {'type': 'mc', 'ts': 131,
         'qf': 'بیماری که دیگوکسین مصرف می‌کند دچار کاهش پتاسیم شده است. چرا پرستار باید نگران باشد؟',
         'qe': 'A client taking digoxin has developed low potassium. Why should the nurse be concerned?',
         'of': ['کاهش پتاسیم اثر کرونوتروپیک منفی دیگوکسین را خنثی می‌کند',
               'کاهش پتاسیم خطر سمیت دیگوکسین را افزایش می‌دهد',
               'کاهش پتاسیم باعث تبدیل دیگوکسین به گلیکوزید قلبی دیگری می‌شود',
               'کاهش پتاسیم نیاز به دوز بالاتر دیگوکسین را ایجاد می‌کند'],
         'oe': ['Low potassium negates the negative chronotropic effect of digoxin',
               'Low potassium increases the risk of digoxin toxicity',
               'Low potassium converts digoxin into another cardiac glycoside',
               'Low potassium creates the need for a higher digoxin dose'],
         'c': 1,
         'wf': 'ویدیو صریحاً می‌گوید هیپوکالمی یا کاهش پتاسیم، خطر سمیت دیگوکسین را افزایش می‌دهد؛ به همین دلیل سطح پتاسیم در طول درمان پایش می‌شود. کاهش پتاسیم اثر دارو را خنثی نمی‌کند و نیاز به دوز بیشتر هم ایجاد نمی‌کند.',
         'we': 'The video states explicitly that hypokalemia increases the risk of digoxin toxicity, which is why potassium is monitored throughout therapy. Low potassium neither negates the drug’s effect nor calls for a higher dose.'},

        {'type': 'cloze', 'ts': 57,
         'qf': 'اثر کرونوتروپیک منفی دیگوکسین باعث می‌شود ضربان قلب {0} شود و اثر اینوتروپیک مثبت آن قدرت انقباض را افزایش می‌دهد.',
         'qe': 'Digoxin’s negative chronotropic effect makes the heart rate {0}, while its positive inotropic effect increases the force of contraction.',
         'blanks': ['کندتر', 'slower'],
         'wf': 'دیگوکسین ضربان قلب را کند و قدرت انقباض را بیشتر می‌کند. همین ترکیب بار کاری قلب را کاهش می‌دهد و خستگی و تنگی نفس ناشی از نارسایی قلبی را بهتر می‌کند.',
         'we': 'Digoxin slows the heart rate while increasing contractile force. That combination lowers cardiac workload and improves the fatigue and dyspnea of heart failure.'},

        {'type': 'cloze', 'ts': 144,
         'qf': 'پادزهر سمیت دیگوکسین، {0} است.',
         'qe': 'The antidote to digoxin toxicity is {0}.',
         'blanks': ['دیگوکسین ایمون فاب', 'digoxin immune Fab'],
         'wf': 'دیگوکسین ایمون فاب آنتی‌بادی اختصاصی است که دیگوکسین را در بدن خنثی می‌کند و به‌عنوان پادزهر در موارد سمیت شدید تجویز می‌شود.',
         'we': 'Digoxin immune Fab is a specific antibody that neutralizes digoxin in the body and is given as the antidote in severe toxicity.'},

        {'type': 'dnd', 'ts': 107,
         'qf': 'اقدامات پرستاری برای بیماری که دیگوکسین دریافت می‌کند را به همان ترتیبی بچینید که در ویدیو بیان می‌شود.',
         'qe': 'Arrange the nursing actions for a client receiving digoxin in the order the video states.',
         'items': ['پایش سطح پتاسیم بیمار در طول درمان',
                   'بررسی نبض بیمار پیش از تجویز دارو',
                   'پایش سطح سرمی دیگوکسین در طول درمان',
                   'خودداری از تجویز دارو اگر نبض کمتر از ۶۰ بار در دقیقه باشد'],
         'keep': ['بررسی نبض بیمار پیش از تجویز دارو',
                  'خودداری از تجویز دارو اگر نبض کمتر از ۶۰ بار در دقیقه باشد',
                  'پایش سطح سرمی دیگوکسین در طول درمان',
                  'پایش سطح پتاسیم بیمار در طول درمان'],
         'wf': 'ویدیو ترتیب مراقبت را چنین بیان می‌کند: نخست بررسی نبض پیش از تجویز، سپس خودداری از دوز در نبض زیر ۶۰، سپس پایش سطح سرمی دیگوکسین و در پایان پایش پتاسیم به‌دلیل خطر سمیت.',
         'we': 'The video gives the nursing order: check the pulse before administration first, then withhold the dose if the rate is under 60, then monitor the serum digoxin level, and potassium last because of the toxicity risk.'},
    ]},
}


def fmt_dur(s):
    return '%d:%02d' % (s // 60, s % 60)


def add_videos():
    p = os.path.join(ROOT, 'data', 'videos.json')
    vids = json.load(open(p, encoding='utf-8'))
    before = len(vids)
    for vid, d in VIDEOS.items():
        if any(x['id'] == vid for x in vids):
            continue
        m = meta[vid]
        d8 = m['date']
        vids.append({'id': vid, 'dur': fmt_dur(m['dur']), 'tr': True,
                     'cat': CAT_FA, 'cat_en': CAT_EN, 'src': 'Level Up RN',
                     'views': m['views'], 'publishedAt': '%s-%s-%s' % (d8[:4], d8[4:6], d8[6:8]),
                     'fa': d['fa'], 'en': d['en'], 'sum': d['sum'], 'sum_en': d['sum_en'],
                     'ch': d['ch'], 'ch_en': d['ch_en']})
    vids.sort(key=lambda x: x.get('publishedAt', ''), reverse=True)
    json.dump(vids, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('videos.json: %d -> %d' % (before, len(vids)))


def write_quizzes():
    d = os.path.join(ROOT, 'quizzes')
    os.makedirs(d, exist_ok=True)
    for vid, q in QUIZZES.items():
        json.dump(q, open(os.path.join(d, vid + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        types = [x['type'] for x in q['questions']]
        print('quizzes/%s.json  %d questions: %s' % (vid, len(types), ','.join(types)))


if __name__ == '__main__':
    add_videos()
    write_quizzes()