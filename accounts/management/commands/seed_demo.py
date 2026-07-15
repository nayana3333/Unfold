from datetime import timedelta
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from accounts.models import Profile
from community.models import Comment as DiscussionComment
from community.models import Discussion, DiscussionLike, Group, GroupMember
from counseling.models import AvailabilitySlot, Booking, Feedback, PsychiatristProfile
from stories.models import Comment, Like, Post, PostImage, SavedPost, Story


class Command(BaseCommand):
    help = "Seed realistic Unfold demo data for portfolio presentations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-demo",
            action="store_true",
            help="Remove previously seeded demo records before recreating them.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset_demo"]:
            self.delete_demo_data()

        users = self.create_users()
        counselors = self.create_counselors(users)
        posts = self.create_posts(users)
        self.create_post_activity(users, posts)
        self.create_stories(users)
        groups = self.create_groups(users)
        discussions = self.create_discussions(users, groups)
        self.create_discussion_activity(users, discussions)
        self.create_care_data(users, counselors)

        self.stdout.write(self.style.SUCCESS("Seeded Unfold demo data successfully."))
        self.stdout.write("Demo login examples:")
        self.stdout.write("  patient: nayanademo / DemoPass123!")
        self.stdout.write("  counselor: dr_maya / DemoPass123!")

    def delete_demo_data(self):
        usernames = self.demo_usernames()
        demo_users = User.objects.filter(username__in=usernames)
        for post in Post.objects.filter(author__in=demo_users).prefetch_related("carousel_images"):
            if post.image:
                post.image.delete(save=False)
            if post.file:
                post.file.delete(save=False)
            for image in post.carousel_images.all():
                image.image.delete(save=False)
            post.delete()
        for story in Story.objects.filter(user__in=demo_users):
            if story.image:
                story.image.delete(save=False)
            if story.video:
                story.video.delete(save=False)
            story.delete()
        for group in Group.objects.filter(creator__in=demo_users):
            if group.cover_image:
                group.cover_image.delete(save=False)
            group.delete()
        demo_counselors = PsychiatristProfile.objects.filter(user__in=demo_users)
        Booking.objects.filter(user__in=demo_users).delete()
        Booking.objects.filter(psychiatrist__in=demo_counselors).delete()
        AvailabilitySlot.objects.filter(psychiatrist__in=demo_counselors).delete()
        for counselor in PsychiatristProfile.objects.filter(user__in=demo_users):
            if counselor.photo:
                counselor.photo.delete(save=False)
            counselor.delete()
        for profile in Profile.objects.filter(user__in=demo_users):
            if profile.image:
                profile.image.delete(save=False)
        demo_users.exclude(is_superuser=True).delete()

    def demo_usernames(self):
        return [
            "nayanademo",
            "asha_writes",
            "meera_codes",
            "hope_anonymous",
            "riya_builds",
            "kavya.design",
            "zoya_reads",
            "tanya_moves",
            "dr_maya",
            "dr_sana",
            "dr_anika",
            "dr_isha",
        ]

    def get_user(self, username, email, first_name, last_name="", role=Profile.ROLE_PATIENT):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            },
        )
        if created:
            user.set_password("DemoPass123!")
            user.save()
        else:
            changed = False
            for field, value in {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }.items():
                if getattr(user, field) != value:
                    setattr(user, field, value)
                    changed = True
            if changed:
                user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = role
        profile.verification_status = Profile.VERIFICATION_APPROVED
        profile.about = self.about_for(username)
        profile.interests = self.interests_for(username)
        profile.bio = self.bio_for(username)
        self.attach_image(profile.image, f"profiles/{username}.png", self.avatar_image(first_name, username))
        profile.save()
        return user

    def create_users(self):
        return {
            "nayana": self.get_user("nayanademo", "nayana.demo@example.com", "Nayana"),
            "asha": self.get_user("asha_writes", "asha@example.com", "Asha"),
            "meera": self.get_user("meera_codes", "meera@example.com", "Meera"),
            "hope": self.get_user("hope_anonymous", "hope@example.com", "Hope"),
            "riya": self.get_user("riya_builds", "riya@example.com", "Riya"),
            "kavya": self.get_user("kavya.design", "kavya@example.com", "Kavya"),
            "zoya": self.get_user("zoya_reads", "zoya@example.com", "Zoya"),
            "tanya": self.get_user("tanya_moves", "tanya@example.com", "Tanya"),
            "maya": self.get_user("dr_maya", "maya.care@example.com", "Maya", "Rao", Profile.ROLE_COUNSELOR),
            "sana": self.get_user("dr_sana", "sana.care@example.com", "Sana", "Iqbal", Profile.ROLE_COUNSELOR),
            "anika": self.get_user("dr_anika", "anika.care@example.com", "Anika", "Menon", Profile.ROLE_COUNSELOR),
            "isha": self.get_user("dr_isha", "isha.care@example.com", "Isha", "Kapoor", Profile.ROLE_COUNSELOR),
        }

    def create_counselors(self, users):
        data = [
            ("maya", "Dr. Maya Rao", "UNF-MH-1021", "Anxiety, trauma-informed care", "English, Hindi, Kannada", 9, "Warm, evidence-led support for anxiety, boundaries, and life transitions.", "4.85"),
            ("sana", "Dr. Sana Iqbal", "UNF-MH-2034", "Career stress, confidence, depression", "English, Hindi, Urdu", 7, "Focused on helping women rebuild confidence through practical care plans.", "4.70"),
            ("anika", "Dr. Anika Menon", "UNF-MH-3088", "Relationships, grief, self-worth", "English, Malayalam, Tamil", 11, "Gentle support for grief, emotional safety, and relationship boundaries.", "4.90"),
            ("isha", "Dr. Isha Kapoor", "UNF-MH-4096", "College pressure, burnout, sleep", "English, Hindi, Punjabi", 6, "Structured care for students balancing ambition, stress, and recovery.", "4.78"),
        ]
        counselors = []
        for key, full_name, license_no, specialization, languages, years, bio, rating in data:
            profile, _ = PsychiatristProfile.objects.update_or_create(
                user=users[key],
                defaults={
                    "full_name": full_name,
                    "license_no": license_no,
                    "specialization": specialization,
                    "languages": languages,
                    "years_experience": years,
                    "bio": bio,
                    "is_verified": True,
                    "is_female": True,
                    "rating": rating,
                    "available_chat": True,
                    "available_voice": True,
                    "available_video": key != "sana",
                },
            )
            self.attach_image(profile.photo, f"psychiatrists/{key}.png", self.avatar_image(full_name, f"doctor-{key}", size=900))
            profile.save(update_fields=["photo"])
            counselors.append(profile)
        return counselors

    def create_posts(self, users):
        post_data = [
            (users["nayana"], "Built my first calm morning routine this week: 20 minutes of walking, no phone, and one clear priority before college.", False, "", ["Morning reset", "No-phone walk", "One priority"]),
            (users["asha"], "Reminder: asking for help early is not weakness. It is maintenance.", False, "", ["Ask early", "Care plan"]),
            (users["hope"], "I said no without overexplaining today. Small win, but it felt huge.", True, "QuietBloom", ["Boundary win"]),
            (users["meera"], "Career prep note: I made a tiny interview tracker and it made the whole process less scary.", False, "", ["Interview tracker", "Project pitch", "Resume proof"]),
            (users["riya"], "Tiny portfolio upgrade idea: show the actual user journey, not only screenshots. Recruiters remember flows.", False, "", ["User flow", "Portfolio polish"]),
            (users["kavya"], "Design note I keep repeating: spacing is a feature. Calm UI makes people trust the product faster.", False, "", ["Spacing", "Trust", "UI system"]),
            (users["zoya"], "Tonight's journal prompt: what would feel lighter if I stopped carrying it alone?", False, "", ["Journal prompt"]),
            (users["tanya"], "A 10-minute stretch between study sessions changed my whole evening. Soft reset, real result.", False, "", ["Stretch reset", "Study break"]),
            (users["nayana"], "Saved this thought for myself: progress can be private before it becomes visible.", False, "", ["Private progress"]),
        ]
        posts = []
        for index, (author, content, is_anonymous, pseudonym, slides) in enumerate(post_data):
            post, _ = Post.objects.update_or_create(
                author=author,
                content=content,
                defaults={
                    "is_anonymous": is_anonymous,
                    "pseudonym": pseudonym,
                    "allow_comments": True,
                },
            )
            for old_image in post.carousel_images.all():
                old_image.image.delete(save=False)
            post.carousel_images.all().delete()
            for position, title in enumerate(slides):
                image = PostImage(post=post, position=position)
                self.attach_image(
                    image.image,
                    f"post_images/carousel/demo-{post.id}-{position + 1}.png",
                    self.post_image(title, content, f"{author.first_name or author.username} on Unfold", index + position),
                )
                image.save()
            posts.append(post)
        return posts

    def create_post_activity(self, users, posts):
        likers = [users["asha"], users["meera"], users["nayana"], users["hope"], users["riya"], users["kavya"], users["zoya"], users["tanya"]]
        for post in posts:
            for user in likers:
                if user != post.author:
                    Like.objects.get_or_create(user=user, post=post)
            SavedPost.objects.get_or_create(user=users["nayana"], post=post)

        comments = [
            (users["asha"], posts[0], "This feels doable. I am trying the no-phone morning idea tomorrow."),
            (users["meera"], posts[1], "Needed this today. Thank you for saying it plainly."),
            (users["nayana"], posts[2], "Proud of this win. Boundaries are hard work."),
            (users["hope"], posts[3], "A tracker sounds useful. Could you share the structure?"),
            (users["riya"], posts[3], "This is exactly the kind of system that makes interviews less chaotic."),
            (users["kavya"], posts[4], "Yes. A flow with before/after screens makes the project feel much more senior."),
            (users["zoya"], posts[5], "Spacing really changes the emotion of a page. This is such a good reminder."),
            (users["tanya"], posts[6], "Writing this down for tonight. It feels gentle but honest."),
            (users["asha"], posts[7], "Soft reset is the phrase I needed today."),
            (users["meera"], posts[8], "Private progress still counts. Saving this."),
        ]
        for user, post, text in comments:
            Comment.objects.get_or_create(user=user, post=post, text=text)

    def create_stories(self, users):
        now = timezone.now()
        story_data = [
            (users["nayana"], "Today: study, breathe, build one small thing.", False, ""),
            (users["asha"], "Water, stretch, then work. Tiny rituals count.", False, ""),
            (users["meera"], "Interview prep sprint: 3 questions, 1 project story.", False, ""),
            (users["riya"], "Portfolio polish day: one flow, one bug fix, one screenshot.", False, ""),
            (users["kavya"], "Design check: reduce noise, increase trust.", False, ""),
            (users["zoya"], "Quiet evening. Good book. Better breathing.", True, "MoonNote"),
        ]
        for index, (user, content, is_anonymous, pseudonym) in enumerate(story_data):
            story, _ = Story.objects.update_or_create(
                user=user,
                content=content,
                defaults={
                    "story_type": "image",
                    "expiry": now + timedelta(hours=24),
                    "is_anonymous": is_anonymous,
                    "pseudonym": pseudonym,
                },
            )
            self.attach_image(story.image, f"stories/images/{user.username}.png", self.story_image(user.first_name or user.username, content, index))
            story.save(update_fields=["image", "story_type", "expiry", "is_anonymous", "pseudonym"])

    def create_groups(self, users):
        group_data = [
            ("Career Confidence Circle", "Interview preparation, resume wins, and confidence building for women starting tech careers.", users["meera"]),
            ("Calm Corner", "A gentle space for anxiety resets, routines, and emotional support.", users["asha"]),
            ("Safe Stories", "Anonymous reflections, support, and healing conversations.", users["nayana"]),
            ("Design Glow-Up", "UI reviews, portfolio polish, product thinking, and clean frontend standards.", users["kavya"]),
            ("Student Reset Club", "Study routines, burnout prevention, and small recovery rituals.", users["tanya"]),
        ]
        groups = []
        for index, (name, description, creator) in enumerate(group_data):
            group, _ = Group.objects.update_or_create(
                name=name,
                defaults={
                    "description": description,
                    "creator": creator,
                    "visibility": "public",
                    "is_active": True,
                },
            )
            self.attach_image(group.cover_image, f"groups/covers/{name.lower().replace(' ', '-')}.png", self.cover_image(name, description, index))
            group.save(update_fields=["cover_image"])
            groups.append(group)
            GroupMember.objects.update_or_create(group=group, user=creator, defaults={"role": "admin"})
            for user in [users["nayana"], users["asha"], users["meera"], users["hope"], users["riya"], users["kavya"], users["zoya"], users["tanya"]]:
                GroupMember.objects.get_or_create(group=group, user=user)
        return groups

    def create_discussions(self, users, groups):
        items = [
            (groups[0], users["meera"], "How I explain this project in interviews", "I am practicing a 60-second pitch: problem, users, features, tech, and impact. What should I improve?", True),
            (groups[0], users["nayana"], "Resume project checklist", "Adding deployment, README screenshots, real test data, and one strong AI feature before applying.", False),
            (groups[1], users["asha"], "Two-minute reset that works for me", "Name five things you see, unclench your jaw, breathe out longer than you breathe in.", True),
            (groups[2], users["hope"], "How do you ask for support?", "I want to ask a friend for help but I keep feeling like a burden.", False),
            (groups[3], users["kavya"], "What makes a page look senior?", "For me: consistent spacing, clear hierarchy, fewer random colors, and real empty states.", True),
            (groups[4], users["tanya"], "Study burnout reset ideas", "What helps when your mind is tired but deadlines are still close?", False),
        ]
        discussions = []
        for group, author, title, content, pinned in items:
            discussion, _ = Discussion.objects.update_or_create(
                group=group,
                title=title,
                defaults={
                    "author": author,
                    "content": content,
                    "is_pinned": pinned,
                    "is_closed": False,
                },
            )
            discussions.append(discussion)
        return discussions

    def create_discussion_activity(self, users, discussions):
        for discussion in discussions:
            for user in [users["nayana"], users["asha"], users["meera"], users["riya"], users["kavya"], users["zoya"]]:
                if user != discussion.author:
                    DiscussionLike.objects.get_or_create(discussion=discussion, user=user)

        comments = [
            (discussions[0], users["nayana"], "Mention the safety angle and role-based dashboards. That sounds strong."),
            (discussions[1], users["meera"], "Screenshots will help a lot. Recruiters understand faster with visuals."),
            (discussions[2], users["hope"], "The longer exhale part really helps me too."),
            (discussions[3], users["asha"], "You can ask with one clear sentence: I am having a hard day, can you sit with me for ten minutes?"),
            (discussions[4], users["riya"], "Also consistent button states. Hover, active, disabled - all of it matters."),
            (discussions[4], users["nayana"], "This is going into my checklist before screenshots."),
            (discussions[5], users["zoya"], "A shower, food, and one tiny next step. Not the whole deadline at once."),
            (discussions[5], users["meera"], "I use a 25-minute sprint and write down exactly what done means."),
        ]
        for discussion, author, content in comments:
            DiscussionComment.objects.get_or_create(discussion=discussion, author=author, content=content)

    def create_care_data(self, users, counselors):
        now = timezone.now()
        slots_by_counselor = {}
        for index, counselor in enumerate(counselors):
            slots_by_counselor[counselor.id] = []
            for offset in range(1, 5):
                start = (now + timedelta(days=offset, hours=10 + index)).replace(minute=0, second=0, microsecond=0)
                end = start + timedelta(minutes=45)
                slot, _ = AvailabilitySlot.objects.update_or_create(
                    psychiatrist=counselor,
                    start=start,
                    end=end,
                    defaults={"is_booked": False},
                )
                slots_by_counselor[counselor.id].append(slot)

        booking_specs = [
            (users["nayana"], counselors[0], slots_by_counselor[counselors[0].id][0], "video", "confirmed", "I want help staying calm before interviews."),
            (users["asha"], counselors[1], slots_by_counselor[counselors[1].id][0], "chat", "pending", "Need help with work stress."),
            (users["meera"], counselors[2], slots_by_counselor[counselors[2].id][0], "voice", "completed", "Follow-up after a difficult week."),
            (users["riya"], counselors[3], slots_by_counselor[counselors[3].id][0], "chat", "confirmed", "Burnout and sleep routine support."),
        ]
        for user, counselor, slot, mode, status, notes in booking_specs:
            booking, _ = Booking.objects.update_or_create(
                user=user,
                psychiatrist=counselor,
                slot=slot,
                defaults={
                    "mode": mode,
                    "status": status,
                    "allow_anonymous": False,
                    "notes": notes,
                },
            )
            slot.is_booked = True
            slot.save(update_fields=["is_booked"])
            if status == "completed":
                Feedback.objects.update_or_create(
                    booking=booking,
                    defaults={
                        "rating": 5,
                        "comment": "The session felt safe, practical, and respectful.",
                    },
                )

    def about_for(self, username):
        values = {
            "nayanademo": "Student developer building confidence through projects, community, and careful routines.",
            "asha_writes": "Writer, listener, and gentle routine builder.",
            "meera_codes": "Frontend learner preparing for web development interviews.",
            "hope_anonymous": "Here to learn, heal, and share quietly.",
            "riya_builds": "Project-first learner turning ideas into portfolio-ready products.",
            "kavya.design": "Frontend designer who cares about hierarchy, spacing, and warm UX.",
            "zoya_reads": "Reader, journal keeper, and believer in soft resets.",
            "tanya_moves": "Movement breaks, study plans, and practical calm.",
        }
        return values.get(username, "Verified counselor on Unfold.")

    def interests_for(self, username):
        values = {
            "nayanademo": "web development, mindfulness, interview prep",
            "asha_writes": "journaling, wellness, peer support",
            "meera_codes": "React, portfolios, confidence",
            "hope_anonymous": "healing, boundaries, calm spaces",
            "riya_builds": "portfolio, Django, product flows",
            "kavya.design": "UI design, Figma, visual systems",
            "zoya_reads": "books, journaling, reflection",
            "tanya_moves": "fitness, study routines, burnout resets",
        }
        return values.get(username, "counseling, safety, mental health")

    def bio_for(self, username):
        values = {
            "nayanademo": "Building, learning, and sharing one small win at a time.",
            "asha_writes": "Soft reminders for hard days.",
            "meera_codes": "Turning projects into confidence.",
            "hope_anonymous": "Choosing quiet courage.",
            "riya_builds": "Building proof, not just plans.",
            "kavya.design": "Making interfaces feel clear and kind.",
            "zoya_reads": "Gentle notes for heavy days.",
            "tanya_moves": "Reset, move, continue.",
        }
        return values.get(username, "Verified Unfold care professional.")

    def attach_image(self, field, path, image_bytes):
        field.save(path, ContentFile(image_bytes), save=False)

    def font(self, size):
        for path in [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
        return ImageFont.load_default()

    def palette_for(self, seed):
        palettes = [
            ("#f77f98", "#ffe3cf", "#1c1719"),
            ("#111111", "#f2eee9", "#f28da3"),
            ("#ff8fa3", "#fff7f1", "#7b3a4a"),
            ("#d94f70", "#f8dfe5", "#171214"),
            ("#2d2926", "#f6d0c6", "#bf4965"),
            ("#fb7185", "#fff1f2", "#312022"),
        ]
        return palettes[sum(ord(char) for char in str(seed)) % len(palettes)]

    def gradient(self, size, primary, secondary):
        width, height = size
        image = Image.new("RGB", size, primary)
        draw = ImageDraw.Draw(image)
        p = tuple(int(primary.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        s = tuple(int(secondary.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = tuple(int(p[i] * (1 - ratio) + s[i] * ratio) for i in range(3))
            draw.line([(0, y), (width, y)], fill=color)
        return image

    def png_bytes(self, image):
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    def fit_text(self, draw, text, font, max_width, max_lines=5):
        words = text.split()
        lines = []
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines[:max_lines]

    def avatar_image(self, name, seed, size=720):
        primary, secondary, ink = self.palette_for(seed)
        image = self.gradient((size, size), primary, secondary)
        draw = ImageDraw.Draw(image)
        draw.ellipse((size * 0.18, size * 0.15, size * 0.82, size * 0.82), fill=(255, 255, 255), outline=None)
        draw.ellipse((size * 0.33, size * 0.24, size * 0.67, size * 0.58), fill=primary)
        draw.rounded_rectangle((size * 0.25, size * 0.55, size * 0.75, size * 0.94), radius=int(size * 0.2), fill=secondary)
        initials = "".join(part[0] for part in name.replace("Dr.", "").split()[:2]).upper() or "U"
        font = self.font(int(size * 0.16))
        box = draw.textbbox((0, 0), initials, font=font)
        draw.text(((size - (box[2] - box[0])) / 2, size * 0.63), initials, fill=ink, font=font)
        return self.png_bytes(image)

    def post_image(self, title, body, author, seed):
        primary, secondary, _ = self.palette_for(seed)
        image = self.gradient((1080, 1350), primary, secondary)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((90, 100, 990, 1250), radius=46, fill=(255, 250, 250))
        draw.rounded_rectangle((130, 140, 950, 430), radius=34, fill=primary)
        draw.text((170, 205), "UNFOLD", font=self.font(34), fill=(255, 255, 255))
        title_font = self.font(74)
        body_font = self.font(36)
        y = 500
        for line in self.fit_text(draw, title, title_font, 760, max_lines=3):
            draw.text((150, y), line, fill="#1d1518", font=title_font)
            y += 86
        y += 20
        for line in self.fit_text(draw, body, body_font, 760, max_lines=5):
            draw.text((150, y), line, fill="#65565b", font=body_font)
            y += 48
        draw.line((150, 1120, 930, 1120), fill="#f1cbd4", width=3)
        draw.text((150, 1160), author, fill="#9d4259", font=self.font(34))
        return self.png_bytes(image)

    def story_image(self, name, content, seed):
        primary, secondary, _ = self.palette_for(seed)
        image = self.gradient((1080, 1920), primary, secondary)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((90, 180, 990, 1740), radius=60, fill=(255, 250, 250))
        draw.text((150, 270), name, fill="#1d1518", font=self.font(64))
        y = 470
        for line in self.fit_text(draw, content, self.font(72), 760, max_lines=6):
            draw.text((150, y), line, fill="#1d1518", font=self.font(72))
            y += 92
        draw.rounded_rectangle((150, 1500, 520, 1580), radius=40, fill=primary)
        draw.text((190, 1518), "Today on Unfold", fill="#ffffff", font=self.font(32))
        return self.png_bytes(image)

    def cover_image(self, name, description, seed):
        primary, secondary, _ = self.palette_for(seed)
        image = self.gradient((1440, 640), primary, secondary)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((80, 80, 1360, 560), radius=44, fill=(255, 250, 250))
        draw.text((150, 170), name, fill="#1d1518", font=self.font(76))
        y = 285
        for line in self.fit_text(draw, description, self.font(42), 1060, max_lines=3):
            draw.text((150, y), line, fill="#65565b", font=self.font(42))
            y += 56
        draw.ellipse((1160, 160, 1280, 280), fill=primary)
        draw.ellipse((1240, 280, 1320, 360), fill="#f5b2c0")
        return self.png_bytes(image)
