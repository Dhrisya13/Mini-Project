from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import *
import re



def home(request):
    return render(request, 'user/home.html')

def get_started(request):
    if request.user.is_authenticated:
        return redirect('health_record')
    else:
        return redirect('user_login')

def check_email(request):
    email = request.GET.get('email', '').strip()
    if email:
        exists = User.objects.filter(email__iexact=email).exists() or User_table.objects.filter(Email__iexact=email).exists()
        if exists:
            return JsonResponse({'exists': True, 'message': 'This email is already registered. Please login.'})
    return JsonResponse({'exists': False})

def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                u = User.objects.get(email__iexact=email)
                user = authenticate(request, username=u.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            login(request, user)
            return JsonResponse({'success': True, 'redirect_url': '/myapp/health-record/'})
        else:
            email_exists = User.objects.filter(email__iexact=email).exists() or User_table.objects.filter(Email__iexact=email).exists()
            if not email_exists:
                return JsonResponse({'success': False, 'message': 'Email not registered. Please register first.'})
            return JsonResponse({'success': False, 'message': 'Invalid email or password.'})

    return render(request, 'user/login.html')

def user_registration(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        dob = request.POST.get('dob', '')
        gender = request.POST.get('gender', '')
        password = request.POST.get('password', '')
        height = request.POST.get('height', '0')
        weight = request.POST.get('weight', '0')
        
        # Validate & parse DOB safely into a date object
        dob_obj = None
        if dob:
            from datetime import datetime, date
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y'):
                try:
                    dob_obj = datetime.strptime(dob, fmt).date()
                    break
                except ValueError:
                    continue

            if dob_obj and dob_obj >= date.today():
                return JsonResponse({
                    'success': False,
                    'message': 'Date of birth cannot be today or a future date. Please select a past date.'
                })

        if not dob_obj and dob:
            dob_obj = None

        if not dob_obj:
            from datetime import date
            dob_obj = date(2000, 1, 1)

        # Check duplicate email
        if User.objects.filter(email__iexact=email).exists() or User_table.objects.filter(Email__iexact=email).exists():
            return JsonResponse({
                'success': False,
                'duplicate_email': True,
                'message': 'This email is already registered. Please login.'
            })
        
        phone_int = int(phone) if phone and phone.isdigit() else 0

        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            user.first_name = name
            user.save()

            user_tab = User_table.objects.create(
                LOGIN=user,
                Full_name=name,
                DOB=dob_obj,
                Gender=gender,
                Email=email,
                PhonenNo=phone_int
            )

            try:
                h_val = float(height) if height else 0.0
                w_val = float(weight) if weight else 0.0
            except ValueError:
                h_val = 0.0
                w_val = 0.0

            Health_record.objects.create(
                User_ID=user_tab,
                Height=h_val,
                Weight=w_val,
                Smoking='',
                Alcohol='',
                Physical_Activity='',
                Sleep_Duration=0.0,
                Water_Intake=0.0
            )

            login(request, user)
            return JsonResponse({'success': True, 'message': 'Account created successfully!'})
        except Exception as e:
            print("Registration Exception:", e)
            return JsonResponse({'success': False, 'message': 'Registration failed. Please check your details and try again.'})

    return render(request, 'user/registration.html')


def user_logout(request):
    logout(request)
    return redirect('home')

def get_user_data(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return None
    user_data = User_table.objects.filter(LOGIN=request.user).first()
    if not user_data and hasattr(request.user, 'email') and request.user.email:
        user_data = User_table.objects.filter(Email__iexact=request.user.email).first()
    if not user_data:
        try:
            full_name = request.user.first_name or request.user.username or "User"
            email = request.user.email or request.user.username or ""
            from datetime import date
            user_data = User_table.objects.create(
                LOGIN=request.user,
                Full_name=full_name,
                DOB=date(2000, 1, 1),
                Gender='Not specified',
                Email=email,
                PhonenNo=0
            )
        except Exception:
            user_data = None
    elif user_data and (user_data.LOGIN is None or user_data.LOGIN != request.user):
        try:
            user_data.LOGIN = request.user
            user_data.save()
        except Exception:
            pass
    return user_data

def health_record(request):
    user_data = get_user_data(request)

    latest_record = Health_record.objects.filter(User_ID=user_data).last() if user_data else None

    if request.method == 'POST':
        dob_raw = request.POST.get('dob', '').strip()
        height = request.POST.get('height', '')
        weight = request.POST.get('weight', '')
        if (not height or height == '0') and latest_record and latest_record.Height > 0:
            height = str(latest_record.Height)
        if (not weight or weight == '0') and latest_record and latest_record.Weight > 0:
            weight = str(latest_record.Weight)

        smoking = request.POST.get('smoking', '').strip()
        alcohol = request.POST.get('alcohol', '').strip()
        activity = request.POST.get('physical_activity', '').strip()
        sleep = request.POST.get('sleep_duration', '').strip()
        water = request.POST.get('water_intake', '').strip()

        if user_data and dob_raw:
            from datetime import datetime, date
            dob_obj = None
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y'):
                try:
                    dob_obj = datetime.strptime(dob_raw, fmt).date()
                    break
                except ValueError:
                    continue
            if dob_obj and dob_obj < date.today():
                user_data.DOB = dob_obj
                user_data.save()

        try:
            h_val = float(height) if height else 0.0
            w_val = float(weight) if weight else 0.0
            h_m = h_val / 100.0 if h_val > 0 else 1.7
            w_kg = w_val if w_val > 0 else 70.0
            bmi = w_kg / (h_m * h_m)
        except ValueError:
            h_val = 0.0
            w_val = 0.0
            bmi = 22.0

        if user_data:
            try:
                Health_record.objects.create(
                    User_ID=user_data,
                    Height=float(height) if height else 0.0,
                    Weight=float(weight) if weight else 0.0,
                    Smoking=smoking,
                    Alcohol=alcohol,
                    Physical_Activity=activity,
                    Sleep_Duration=float(sleep) if sleep else 0.0,
                    Water_Intake=float(water) if water else 0.0
                )
            except Exception as e:
                print("Error saving health record:", e)

        return JsonResponse({
            'success': True,
            'message': 'Health record saved successfully!',
            'bmi': round(bmi, 1)
        })


    full_name = ""
    email = ""
    dob = ""
    gender = ""
    phone = ""
    height = ""
    weight = ""
    smoking = ""
    sleep_duration = ""
    alcohol = ""
    water_intake = ""
    physical_activity = ""

    if user_data:
        full_name = user_data.Full_name or ""
        email = user_data.Email or ""
        dob = user_data.DOB.strftime('%Y-%m-%d') if user_data.DOB else ""
        gender = user_data.Gender or ""
        phone = user_data.PhonenNo or ""
    elif hasattr(request, 'user') and request.user.is_authenticated:
        full_name = request.user.first_name or request.user.username or ""
        email = request.user.email or ""

    if latest_record:
        height = f"{latest_record.Height:.0f}" if latest_record.Height > 0 else ""
        weight = f"{latest_record.Weight:.0f}" if latest_record.Weight > 0 else ""
        smoking = latest_record.Smoking or ""
        sleep_duration = f"{latest_record.Sleep_Duration}" if latest_record.Sleep_Duration > 0 else ""
        alcohol = latest_record.Alcohol or ""
        water_intake = f"{latest_record.Water_Intake}" if latest_record.Water_Intake > 0 else ""
        physical_activity = latest_record.Physical_Activity or ""

    context = {
        'user_data': user_data,
        'full_name': full_name,
        'email': email,
        'dob': dob,
        'gender': gender,
        'phone': phone,
        'height': height,
        'weight': weight,
        'smoking': smoking,
        'sleep_duration': sleep_duration,
        'alcohol': alcohol,
        'water_intake': water_intake,
        'physical_activity': physical_activity,
    }
    return render(request, 'user/HealthRecord.html', context)






def view_profile(request):
    if not (hasattr(request, 'user') and request.user.is_authenticated):
        return redirect('user_login')

    user_data = User_table.objects.filter(LOGIN=request.user).first()

    # Fallback: if User_table doesn't exist for this user, create standard record
    if not user_data:
        try:
            full_name = request.user.first_name or request.user.username
            email = request.user.email or request.user.username
            from datetime import date
            user_data = User_table.objects.create(
                LOGIN=request.user,
                Full_name=full_name,
                DOB=date(2000, 1, 1),
                Gender='Not specified',
                Email=email,
                PhonenNo=0
            )
        except Exception:
            user_data = None

    health_rec = Health_record.objects.filter(User_ID=user_data).last() if user_data else None

    full_name = user_data.Full_name if user_data and user_data.Full_name else (request.user.first_name or request.user.username or "User")
    email = user_data.Email if user_data and user_data.Email else (request.user.email or "Not provided")

    # Safe DOB & Age calculation
    dob_formatted = "Not provided"
    age_str = "Not provided"
    if user_data and user_data.DOB:
        from datetime import datetime, date
        dob_val = user_data.DOB
        dob_obj = None
        if isinstance(dob_val, str):
            try:
                dob_obj = datetime.strptime(dob_val, '%Y-%m-%d').date()
            except ValueError:
                dob_obj = None
        elif isinstance(dob_val, (datetime, date)):
            dob_obj = dob_val if isinstance(dob_val, date) else dob_val.date()

        if dob_obj:
            dob_formatted = dob_obj.strftime('%B %d, %Y')
            today = date.today()
            calculated_age = today.year - dob_obj.year - ((today.month, today.day) < (dob_obj.month, dob_obj.day))
            if calculated_age >= 0:
                age_str = f"{calculated_age} years"
        else:
            dob_formatted = str(dob_val)

    gender = user_data.Gender.capitalize() if user_data and user_data.Gender else "Not provided"
    phone = user_data.PhonenNo if user_data and user_data.PhonenNo else "Not provided"
    patient_id = f"#HM-2024-{request.user.id:04d}"

    height = f"{health_rec.Height:.0f} cm" if health_rec and health_rec.Height > 0 else "Not recorded"
    weight = f"{health_rec.Weight:.0f} kg" if health_rec and health_rec.Weight > 0 else "Not recorded"

    bmi_val = None
    bmi_status = "Not calculated"
    if health_rec and health_rec.Height > 0 and health_rec.Weight > 0:
        h_m = health_rec.Height / 100.0
        calc_bmi = health_rec.Weight / (h_m * h_m)
        bmi_val = f"{calc_bmi:.1f}"
        if calc_bmi < 18.5:
            bmi_status = "Underweight"
        elif calc_bmi < 25.0:
            bmi_status = "Normal Weight"
        elif calc_bmi < 30.0:
            bmi_status = "Overweight"
        else:
            bmi_status = "Obese"

    # Lifestyle details formatting
    smoking = health_rec.Smoking if health_rec and health_rec.Smoking else "Not specified"
    sleep_duration = f"{health_rec.Sleep_Duration:g} hrs/day" if health_rec and health_rec.Sleep_Duration > 0 else "Not recorded"
    alcohol = health_rec.Alcohol if health_rec and health_rec.Alcohol else "Not specified"
    water_intake = f"{health_rec.Water_Intake:g} L/day" if health_rec and health_rec.Water_Intake > 0 else "Not recorded"
    physical_activity = health_rec.Physical_Activity if health_rec and health_rec.Physical_Activity else "Not specified"

    # Diabetes Prediction & Clinical Risk Details
    latest_prediction = None
    latest_risk = None
    recommendations = None
    if user_data:
        try:
            pred_detail = Prediction_Details.objects.filter(Record_ID__User_ID=user_data).last()
            if pred_detail:
                latest_prediction = pred_detail
                latest_risk = Prediction_Risk.objects.filter(Prediction_ID=latest_prediction).last()
                if latest_risk:
                    recommendations = Reccomendation_table.objects.filter(Risk_ID=latest_risk).first()
        except Exception as e:
            print("Error retrieving profile predictions:", e)

    context = {
        'user_data': user_data,
        'full_name': full_name,
        'email': email,
        'dob': dob_formatted,
        'age': age_str,
        'gender': gender,
        'phone': phone,
        'patient_id': patient_id,
        'height': height,
        'weight': weight,
        'bmi': bmi_val or "N/A",
        'bmi_status': bmi_status,
        'smoking': smoking,
        'sleep_duration': sleep_duration,
        'alcohol': alcohol,
        'water_intake': water_intake,
        'physical_activity': physical_activity,
        'health_rec': health_rec,
        'latest_prediction': latest_prediction,
        'latest_risk': latest_risk,
        'recommendations': recommendations,
    }
    return render(request, 'user/view_profile.html', context)


def forgot_password(request):
    return render(request, 'user/forgot_password.html')

def edit_profile(request):
    if not (hasattr(request, 'user') and request.user.is_authenticated):
        return redirect('user_login')

    user_data = User_table.objects.filter(LOGIN=request.user).first()
    health_rec = Health_record.objects.filter(User_ID=user_data).last() if user_data else None

    if request.method == 'POST':
        full_name = request.POST.get('fullName', '').strip()
        dob = request.POST.get('dob', '')
        email = request.POST.get('email', '').strip()
        gender = request.POST.get('gender', '')
        phone = request.POST.get('phone', '').strip()
        height = request.POST.get('height', '0')
        weight = request.POST.get('weight', '0')
        smoking = request.POST.get('smoking', '')
        sleep = request.POST.get('sleep', '0')
        alcohol = request.POST.get('alcohol', '')
        water = request.POST.get('water', '0')
        activity = request.POST.get('activity', '')

        # Update User_table
        if user_data:
            if full_name: user_data.Full_name = full_name
            if dob:
                from datetime import datetime, date
                dob_obj = None
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y'):
                    try:
                        dob_obj = datetime.strptime(dob, fmt).date()
                        break
                    except ValueError:
                        continue
                if dob_obj and dob_obj < date.today():
                    user_data.DOB = dob_obj
            if gender: user_data.Gender = gender
            if phone:
                try:
                    user_data.PhonenNo = int(phone)
                except ValueError:
                    pass
            user_data.save()

        # Update Django User
        if full_name:
            request.user.first_name = full_name
            request.user.save()

        # Update or Create Health_record
        if user_data:
            try:
                h_val = float(height) if height and float(height) > 0 else (health_rec.Height if health_rec else 0.0)
                w_val = float(weight) if weight and float(weight) > 0 else (health_rec.Weight if health_rec else 0.0)
                s_val = float(sleep) if sleep and float(sleep) > 0 else (health_rec.Sleep_Duration if health_rec else 0.0)
                wat_val = float(water) if water and float(water) > 0 else (health_rec.Water_Intake if health_rec else 0.0)
            except ValueError:
                h_val, w_val, s_val, wat_val = 0.0, 0.0, 0.0, 0.0

            if health_rec:
                health_rec.Height = h_val
                health_rec.Weight = w_val
                if smoking: health_rec.Smoking = smoking
                if alcohol: health_rec.Alcohol = alcohol
                if activity: health_rec.Physical_Activity = activity
                health_rec.Sleep_Duration = s_val
                health_rec.Water_Intake = wat_val
                health_rec.save()
            else:
                Health_record.objects.create(
                    User_ID=user_data,
                    Height=h_val,
                    Weight=w_val,
                    Smoking=smoking,
                    Alcohol=alcohol,
                    Physical_Activity=activity,
                    Sleep_Duration=s_val,
                    Water_Intake=wat_val
                )

        return redirect('view_profile')

    full_name = user_data.Full_name if user_data and user_data.Full_name else (request.user.first_name or request.user.username)
    email = user_data.Email if user_data and user_data.Email else (request.user.email or "")
    dob = user_data.DOB.strftime('%Y-%m-%d') if user_data and user_data.DOB else ""
    gender = user_data.Gender or ""
    phone = user_data.PhonenNo if user_data and user_data.PhonenNo else ""

    height = f"{health_rec.Height:.0f}" if health_rec and health_rec.Height > 0 else ""
    weight = f"{health_rec.Weight:.0f}" if health_rec and health_rec.Weight > 0 else ""
    smoking = health_rec.Smoking if health_rec else ""
    sleep = f"{health_rec.Sleep_Duration}" if health_rec and health_rec.Sleep_Duration > 0 else ""
    alcohol = health_rec.Alcohol if health_rec else ""
    water = f"{health_rec.Water_Intake}" if health_rec and health_rec.Water_Intake > 0 else ""
    activity = health_rec.Physical_Activity if health_rec else ""

    context = {
        'full_name': full_name,
        'email': email,
        'dob': dob,
        'gender': gender,
        'phone': phone,
        'height': height,
        'weight': weight,
        'smoking': smoking,
        'sleep': sleep,
        'alcohol': alcohol,
        'water': water,
        'activity': activity,
    }
    return render(request, 'user/EditProfile.html', context)


def predict_risk(request):
    user_data = get_user_data(request)

    health_rec = Health_record.objects.filter(User_ID=user_data).last() if user_data else None

    # Calculate current BMI
    bmi_val = 22.0
    bmi_status_str = "22.0 (Normal)"
    if health_rec and health_rec.Height > 0 and health_rec.Weight > 0:
        h_m = health_rec.Height / 100.0
        bmi_val = round(health_rec.Weight / (h_m * h_m), 1)
        if bmi_val < 18.5:
            cat = "Underweight"
        elif bmi_val < 25.0:
            cat = "Normal"
        elif bmi_val < 30.0:
            cat = "Overweight"
        else:
            cat = "Obese"
        bmi_status_str = f"{bmi_val} ({cat})"

    latest_pred = None
    latest_risk = None
    latest_rec = None
    if user_data or (hasattr(request, 'user') and request.user.is_authenticated):
        from django.db.models import Q
        q_filter = Q(Record_ID__User_ID__LOGIN=request.user)
        if user_data:
            q_filter |= Q(Record_ID__User_ID=user_data)
        latest_pred = Prediction_Details.objects.filter(q_filter).select_related('Record_ID').order_by('-id').first()
        if latest_pred:
            latest_risk = Prediction_Risk.objects.filter(Prediction_ID=latest_pred).last()
            if latest_risk:
                latest_rec = Reccomendation_table.objects.filter(Risk_ID=latest_risk).first()

    if request.method == 'POST':
        from datetime import date
        try:
            pregnancies = int(request.POST.get('pregnancies', 0) or 0)
            glucose = float(request.POST.get('glucose', 100) or 100)

            systolic_raw = request.POST.get('systolic_bp', '').strip()
            diastolic_raw = request.POST.get('diastolic_bp', '').strip()

            if systolic_raw or diastolic_raw:
                try:
                    systolic_bp = float(systolic_raw) if systolic_raw else 115.0
                    diastolic_bp = float(diastolic_raw) if diastolic_raw else 75.0
                except ValueError:
                    systolic_bp, diastolic_bp = 115.0, 75.0
                bp = diastolic_bp
            else:
                raw_bp = request.POST.get('blood_pressure', '').strip()
                try:
                    bp = float(raw_bp) if raw_bp else 75.0
                except ValueError:
                    bp = 75.0
                systolic_bp = 115.0
                diastolic_bp = bp

            # Evaluate Analyzed Blood Pressure Range Category
            if systolic_bp >= 180 or diastolic_bp >= 120:
                bp_category = "Hypertensive Crisis"
                bp_range_str = "≥180 / ≥120 mm Hg"
                bp_color = "high"
            elif systolic_bp >= 140 or diastolic_bp >= 90:
                bp_category = "Stage 2 Hypertension"
                bp_range_str = "≥140 / ≥90 mm Hg"
                bp_color = "high"
            elif (130 <= systolic_bp <= 139) or (80 <= diastolic_bp <= 89):
                bp_category = "Stage 1 Hypertension"
                bp_range_str = "130-139 / 80-89 mm Hg"
                bp_color = "moderate"
            elif (120 <= systolic_bp <= 129) and diastolic_bp < 80:
                bp_category = "Elevated Blood Pressure"
                bp_range_str = "120-129 / <80 mm Hg"
                bp_color = "moderate"
            else:
                bp_category = "Normal (Optimal BP)"
                bp_range_str = "<120 / <80 mm Hg"
                bp_color = "low"

            skin = float(request.POST.get('skin_thickness', 20) or 20)
            pedigree = float(request.POST.get('pedigree', 0.47) or 0.47)

            insulin_fasting_raw = request.POST.get('insulin_fasting', '').strip()
            insulin_post_raw = request.POST.get('insulin_post_fasting', '').strip()
            legacy_insulin = float(request.POST.get('insulin', 80) or 80)

            has_fasting = bool(insulin_fasting_raw)
            has_post = bool(insulin_post_raw)

            try:
                insulin_fasting = float(insulin_fasting_raw) if has_fasting else 0.0
            except ValueError:
                insulin_fasting = 0.0
                has_fasting = False

            try:
                insulin_post_fasting = float(insulin_post_raw) if has_post else 0.0
            except ValueError:
                insulin_post_fasting = 0.0
                has_post = False

            if has_fasting and has_post:
                insulin = max(insulin_fasting, insulin_post_fasting)
                insulin_diff = round(insulin_post_fasting - insulin_fasting, 1)
                insulin_ratio = str(round(insulin_post_fasting / insulin_fasting, 1)) if insulin_fasting > 0 else "N/A"
                if insulin_fasting > 25:
                    insulin_eval = f"High Fasting Insulin ({insulin_fasting} mu U/ml) indicates baseline insulin resistance. After fasting response: {insulin_post_fasting} mu U/ml."
                elif insulin_post_fasting > 166:
                    insulin_eval = f"Elevated After Fasting Spike ({insulin_post_fasting} mu U/ml). Fasting: {insulin_fasting} mu U/ml (Shift: +{insulin_diff} mu U/ml)."
                elif insulin_diff > 0:
                    insulin_eval = f"Normal Response Shift: Fasting {insulin_fasting} mu U/ml → After Fasting {insulin_post_fasting} mu U/ml (+{insulin_diff} mu U/ml, {insulin_ratio}x fold change)."
                else:
                    insulin_eval = f"After Fasting level ({insulin_post_fasting} mu U/ml) is lower or equal to Fasting level ({insulin_fasting} mu U/ml)."
            elif has_post:
                insulin = insulin_post_fasting
                insulin_diff = "Single Reading"
                insulin_ratio = "N/A"
                if insulin_post_fasting > 166:
                    insulin_eval = f"High After Fasting Insulin ({insulin_post_fasting} mu U/ml). Elevated postprandial insulin level evaluated for risk prediction."
                else:
                    insulin_eval = f"Single Checkup Reading: Risk prediction evaluated using After Fasting Insulin level ({insulin_post_fasting} mu U/ml)."
            elif has_fasting:
                insulin = insulin_fasting
                insulin_diff = "Single Reading"
                insulin_ratio = "N/A"
                if insulin_fasting > 25:
                    insulin_eval = f"High Fasting Insulin ({insulin_fasting} mu U/ml). Indicates baseline insulin resistance."
                else:
                    insulin_eval = f"Single Checkup Reading: Risk prediction evaluated using Before Fasting Insulin level ({insulin_fasting} mu U/ml)."
            else:
                insulin = legacy_insulin
                insulin_diff = "N/A"
                insulin_ratio = "N/A"
                insulin_eval = f"Default/Legacy Insulin reading evaluated ({legacy_insulin} mu U/ml)."

            bmi_override = request.POST.get('bmi', '').strip()
            if bmi_override and not bmi_override.startswith('0'):
                try:
                    bmi_val = float(bmi_override.split()[0])
                except ValueError:
                    pass
        except ValueError:
            pregnancies, glucose, bp, skin, insulin, pedigree = 0, 100.0, 80.0, 20.0, 80.0, 0.47
            has_fasting, has_post = False, True
            insulin_fasting, insulin_post_fasting = 0.0, 80.0
            insulin_diff, insulin_ratio = "Single Reading", "N/A"
            insulin_eval = "Single checkup reading evaluated."

        # User Age for ML prediction
        user_age = 30
        if user_data and user_data.DOB:
            try:
                from datetime import date
                today = date.today()
                dob_val = user_data.DOB
                if hasattr(dob_val, 'year'):
                    user_age = today.year - dob_val.year - ((today.month, today.day) < (dob_val.month, dob_val.day))
            except Exception:
                user_age = 30

        # Attempt prediction using trained Machine Learning model in train.py
        try:
            from .train import predict_single_sample
            ml_res = predict_single_sample({
                'Pregnancies': pregnancies,
                'Glucose': glucose,
                'BloodPressure': bp,
                'systolic_bp': systolic_bp,
                'diastolic_bp': diastolic_bp,
                'SkinThickness': skin,
                'Insulin': insulin,
                'BMI': bmi_val,
                'DiabetesPedigreeFunction': pedigree,
                'Age': user_age
            })
            risk_score = ml_res['risk_score']
            risk_level = ml_res['risk_level']
        except Exception as e:
            print("ML prediction fallback to clinical algorithm:", e)
            score = 5
            if glucose >= 200:
                score += 65
            elif glucose >= 126:
                score += 45
            elif glucose >= 100:
                score += 25

            if bmi_val >= 35:
                score += 30
            elif bmi_val >= 30:
                score += 20
            elif bmi_val >= 25:
                score += 10

            if systolic_bp >= 140 or diastolic_bp >= 90:
                score += 45
            elif (130 <= systolic_bp <= 139) or (80 <= diastolic_bp <= 89):
                score += 28
            elif (120 <= systolic_bp <= 129) and diastolic_bp < 80:
                score += 15

            if pedigree >= 0.8:
                score += 15
            elif pedigree >= 0.5:
                score += 8

            if insulin > 25:
                score += 30
            elif insulin > 10:
                score += 18
            elif insulin >= 3:
                score += 5

            if skin > 30:
                score += 5
            if pregnancies >= 3:
                score += 5

            risk_score = round(min(98.5, max(5.0, score)), 1)

            if risk_score > 65.0 or glucose >= 200:
                risk_level = "High Risk"
            elif risk_score >= 40.0 or glucose >= 126 or (systolic_bp >= 140 or diastolic_bp >= 90):
                risk_level = "Moderate Risk"
            else:
                risk_level = "Low Risk"

        if risk_level == "High Risk" or risk_score > 65.0:
            risk_level = "High Risk"
            diet = "Strict low-carbohydrate, low-glycemic index diet with high fiber and minimal refined sugars."
            exercise = "45 minutes of daily structured aerobic exercise (brisk walking, cycling) and mild strength training."
            water = "3.0 Liters per day"
            sleep = "7.5 - 8.0 Hours per day"
            weight_mgmt = "Aim for 5-10% gradual weight loss under clinical guidance."
            doctor_advisory = "You have to see a doctor immediately for a diabetes checkup."
        elif risk_level == "Moderate Risk" or risk_score >= 40.0:
            risk_level = "Moderate Risk"
            diet = "Balanced diet rich in whole grains, green vegetables, lean protein, and reduced sugar intake."
            exercise = "30 minutes of moderate physical activity at least 5 days a week."
            water = "2.5 - 3.0 Liters per day"
            sleep = "7.0 - 8.0 Hours per day"
            weight_mgmt = "Maintain healthy weight through consistent daily calorie control."
            doctor_advisory = ""
        else:
            risk_level = "Low Risk"
            diet = "Healthy balanced diet focusing on fresh fruits, vegetables, and unrefined grains."
            exercise = "Regular active lifestyle with 150 minutes of moderate activity per week."
            water = "2.5 Liters per day"
            sleep = "7.0 - 8.0 Hours per day"
            weight_mgmt = "Current weight is in a healthy range. Continue current wellness habits."
            doctor_advisory = ""

        # Save into database if authenticated / user_data available
        if user_data:
            try:
                calc_h = health_rec.Height if (health_rec and health_rec.Height > 0) else 170.0
                calc_w = round(bmi_val * ((calc_h / 100.0) ** 2), 1) if bmi_val > 0 else (health_rec.Weight if health_rec else 70.0)

                if not health_rec:
                    health_rec = Health_record.objects.create(
                        User_ID=user_data,
                        Height=calc_h,
                        Weight=calc_w,
                        Smoking='',
                        Alcohol='',
                        Physical_Activity='',
                        Sleep_Duration=0.0,
                        Water_Intake=0.0
                    )
                else:
                    if calc_w > 0:
                        health_rec.Weight = calc_w
                        health_rec.save()

                pred_detail = Prediction_Details.objects.create(
                    Record_ID=health_rec,
                    Pregnancies=pregnancies,
                    Glucose=glucose,
                    Blood_Pressure=bp,
                    Skin_Thickness=skin,
                    Insulin=insulin,
                    Diabetes_pedigree=pedigree
                )

                pred_risk = Prediction_Risk.objects.create(
                    Prediction_ID=pred_detail,
                    Risk_level=risk_level,
                    Prediction_date=date.today()
                )

                Reccomendation_table.objects.create(
                    Risk_ID=pred_risk,
                    Diet_plan=diet,
                    Exercise_plan=exercise,
                    Water_intake=water,
                    Sleep_intake=sleep,
                    weight_management=weight_mgmt
                )
            except Exception as e:
                print("Error saving prediction record:", e)

        # Parameter range evaluation for Glucose (ADA criteria)
        if glucose >= 200:
            glucose_level = "Very High"
            glucose_range_str = "≥200 mg/dL"
            glucose_interp = "Markedly elevated; diabetes may be present"
            glucose_color = "high"
        elif glucose >= 126:
            glucose_level = "High"
            glucose_range_str = "126-199 mg/dL"
            glucose_interp = "Diabetes range if confirmed"
            glucose_color = "high"
        elif glucose >= 100:
            glucose_level = "Moderate"
            glucose_range_str = "100-125 mg/dL"
            glucose_interp = "Prediabetes range"
            glucose_color = "moderate"
        else:
            glucose_level = "Low"
            glucose_range_str = "<100 mg/dL"
            glucose_interp = "Normal fasting glucose"
            glucose_color = "low"

        # Parameter range evaluation for Fasting Insulin
        if has_fasting:
            if insulin_fasting > 25:
                insulin_level = "High"
                insulin_range_str = ">25 µIU/mL"
                insulin_interp = "High baseline insulin resistance"
            elif insulin_fasting > 10:
                insulin_level = "Elevated"
                insulin_range_str = "11-25 µIU/mL"
                insulin_interp = "Elevated baseline insulin level"
            elif insulin_fasting >= 3:
                insulin_level = "Normal / Lower"
                insulin_range_str = "3-10 µIU/mL"
                insulin_interp = "Normal baseline fasting insulin"
            else:
                insulin_level = "Low"
                insulin_range_str = "<3 µIU/mL"
                insulin_interp = "Low fasting insulin"
        else:
            insulin_level = "Not provided"
            insulin_range_str = "N/A"
            insulin_interp = "N/A"

        return JsonResponse({
            'success': True,
            'risk_level': risk_level,
            'risk_score': risk_score,
            'prediction_date': date.today().strftime('%B %d, %Y'),
            'glucose': glucose,
            'glucose_level': glucose_level,
            'glucose_range': glucose_range_str,
            'glucose_interp': glucose_interp,
            'glucose_color': glucose_color,
            'systolic_bp': int(systolic_bp),
            'diastolic_bp': int(diastolic_bp),
            'bp_reading': f"{int(systolic_bp)} / {int(diastolic_bp)} mm Hg",
            'bp_category': bp_category,
            'bp_range': bp_range_str,
            'bp_color': bp_color,
            'insulin_fasting': f"{insulin_fasting} mu U/ml" if has_fasting else "Not provided",
            'insulin_post_fasting': f"{insulin_post_fasting} mu U/ml" if has_post else "Not provided",
            'insulin_level': insulin_level,
            'insulin_range': insulin_range_str,
            'insulin_interp': insulin_interp,
            'insulin_diff': str(insulin_diff),
            'insulin_ratio': str(insulin_ratio),
            'insulin_eval': insulin_eval,
            'diet': diet,
            'exercise': exercise,
            'water': water,
            'sleep': sleep,
            'weight_mgmt': weight_mgmt,
            'doctor_advisory': doctor_advisory
        })

    context = {
        'bmi_val': bmi_val,
        'bmi_status_str': bmi_status_str,
        'user_data': user_data,
        'latest_pred': latest_pred,
        'latest_risk': latest_risk,
        'latest_rec': latest_rec,
    }
    return render(request, 'user/predict_risk.html', context)


def add_prediction(request):
    if request.method == 'POST':
        pregnancies = request.POST.get('Pregnancies', request.POST.get('pregnancies', 0))
        glucose = request.POST.get('Glucose', request.POST.get('glucose', 100))
        bp = request.POST.get('BloodPressure', request.POST.get('blood_pressure', 80))
        skin = request.POST.get('SkinThickness', request.POST.get('skin_thickness', 20))
        insulin = request.POST.get('Insulin', request.POST.get('insulin', 80))
        bmi = request.POST.get('BMI', request.POST.get('bmi', 25.0))
        pedigree = request.POST.get('DiabetesPedigreeFunction', request.POST.get('pedigree', 0.47))
        age = request.POST.get('Age', request.POST.get('age', None))
        if not age:
            age = 30
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_data = User_table.objects.filter(LOGIN=request.user).first()
                if user_data and user_data.DOB:
                    try:
                        from datetime import date
                        today = date.today()
                        dob_val = user_data.DOB
                        if hasattr(dob_val, 'year'):
                            age = today.year - dob_val.year - ((today.month, today.day) < (dob_val.month, dob_val.day))
                    except Exception:
                        age = 30

        # Perform ML prediction using train.py
        from .train import predict_single_sample
        res = predict_single_sample({
            'Pregnancies': pregnancies,
            'Glucose': glucose,
            'BloodPressure': bp,
            'SkinThickness': skin,
            'Insulin': insulin,
            'BMI': bmi,
            'DiabetesPedigreeFunction': pedigree,
        })

        # Override condition for severely elevated glucose
        try:
            g_num = float(glucose or 0)
        except ValueError:
            g_num = 0

        if g_num >= 200:
            res['risk_score'] = max(res['risk_score'], 70.0)

        # Personalized Recommendations & Threshold Mapping (<40% Low, 40-65% Moderate, >65% High)
        risk_score = res['risk_score']

        if risk_score > 65.0:
            risk_level = "High Risk"
            diet = "Strict low-carbohydrate, low-glycemic index diet with high fiber and minimal refined sugars."
            exercise = "45 minutes of daily structured aerobic exercise (brisk walking, cycling) and mild strength training."
            water = "3.0 Liters per day"
            sleep = "7.5 - 8.0 Hours per day"
            weight_mgmt = "Aim for 5-10% gradual weight loss under clinical guidance."
            doctor_advisory = "You have to see a doctor immediately for a diabetes checkup."
        elif risk_score >= 40.0:
            risk_level = "Moderate Risk"
            diet = "Balanced diet rich in whole grains, green vegetables, lean protein, and reduced sugar intake."
            exercise = "30 minutes of moderate physical activity at least 5 days a week."
            water = "2.5 - 3.0 Liters per day"
            sleep = "7.0 - 8.0 Hours per day"
            weight_mgmt = "Maintain healthy weight through consistent daily calorie control."
            doctor_advisory = ""
        else:
            risk_level = "Low Risk"
            diet = "Healthy balanced diet focusing on fresh fruits, vegetables, and unrefined grains."
            exercise = "Regular active lifestyle with 150 minutes of moderate activity per week."
            water = "2.5 Liters per day"
            sleep = "7.0 - 8.0 Hours per day"
            weight_mgmt = "Current weight is in a healthy range. Continue current wellness habits."
            doctor_advisory = ""

        res['risk_level'] = risk_level

        res.update({
            'diet': diet,
            'exercise': exercise,
            'water': water,
            'sleep': sleep,
            'weight_mgmt': weight_mgmt
        })

        # Save to database if user is authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                from datetime import date
                user_data = User_table.objects.filter(LOGIN=request.user).first()
                if user_data:
                    health_rec = Health_record.objects.filter(User_ID=user_data).last()
                    if not health_rec:
                        h_val = 170.0
                        w_val = float(bmi) * ((h_val/100.0) ** 2) if float(bmi or 0) > 0 else 70.0
                        health_rec = Health_record.objects.create(
                            User_ID=user_data,
                            Height=h_val,
                            Weight=round(w_val, 1),
                            Smoking='',
                            Alcohol='',
                            Physical_Activity='',
                            Sleep_Duration=0.0,
                            Water_Intake=0.0
                        )

                    pred_detail = Prediction_Details.objects.create(
                        Record_ID=health_rec,
                        Pregnancies=int(pregnancies or 0),
                        Glucose=float(glucose or 100),
                        Blood_Pressure=float(bp or 80),
                        Skin_Thickness=float(skin or 20),
                        Insulin=float(insulin or 80),
                        Diabetes_pedigree=float(pedigree or 0.47)
                    )

                    pred_risk = Prediction_Risk.objects.create(
                        Prediction_ID=pred_detail,
                        Risk_level=risk_level,
                        Prediction_date=date.today()
                    )

                    Reccomendation_table.objects.create(
                        Risk_ID=pred_risk,
                        Diet_plan=diet,
                        Exercise_plan=exercise,
                        Water_intake=water,
                        Sleep_intake=sleep,
                        weight_management=weight_mgmt
                    )

                    # Health_History.objects.create(
                    #     User_ID=user_data,
                    #     Prediction_ID=pred_detail
                    # )
            except Exception as e:
                print("Error saving prediction database record:", e)

        return render(request, 'user/view_prediction.html', {'result': res})

    return render(request, 'user/add_prediction.html')


def view_prediction_page(request):
    user_data = get_user_data(request)

    result = None
    if user_data or (hasattr(request, 'user') and request.user.is_authenticated):
        try:
            pred_id = request.GET.get('id')
            from django.db.models import Q
            q_filter = Q(Record_ID__User_ID__LOGIN=request.user)
            if user_data:
                q_filter |= Q(Record_ID__User_ID=user_data)

            if pred_id:
                pred_detail = Prediction_Details.objects.filter(Q(id=pred_id) & q_filter).first()
            else:
                pred_detail = Prediction_Details.objects.filter(q_filter).order_by('-id').first()

            if pred_detail:
                pred_risk = Prediction_Risk.objects.filter(Prediction_ID=pred_detail).last()
                recommendations = Reccomendation_table.objects.filter(Risk_ID=pred_risk).first() if pred_risk else None

                health_rec = pred_detail.Record_ID
                h_m = health_rec.Height / 100.0 if (health_rec and health_rec.Height > 0) else 1.7
                bmi_calc = round(health_rec.Weight / (h_m * h_m), 1) if (health_rec and health_rec.Weight > 0) else 25.0

                user_age = 30
                if user_data and user_data.DOB:
                    try:
                        from datetime import date
                        today = date.today()
                        dob_val = user_data.DOB
                        if hasattr(dob_val, 'year'):
                            user_age = today.year - dob_val.year - ((today.month, today.day) < (dob_val.month, dob_val.day))
                    except Exception:
                        user_age = 30

                from .train import predict_single_sample
                result = predict_single_sample({
                    'Pregnancies': pred_detail.Pregnancies,
                    'Glucose': pred_detail.Glucose,
                    'BloodPressure': pred_detail.Blood_Pressure,
                    'SkinThickness': pred_detail.Skin_Thickness,
                    'Insulin': pred_detail.Insulin,
                    'BMI': bmi_calc,
                    'DiabetesPedigreeFunction': pred_detail.Diabetes_pedigree,
                    'Age': user_age
                })

                all_user_preds = list(Prediction_Details.objects.filter(q_filter).order_by('id').values_list('id', flat=True))
                if pred_detail.id in all_user_preds:
                    user_seq_num = all_user_preds.index(pred_detail.id) + 1
                else:
                    user_seq_num = 1

                result['id'] = pred_detail.id
                result['assessment_num'] = user_seq_num
                if pred_risk:
                    result['risk_level'] = pred_risk.Risk_level
                    if pred_risk.Prediction_date:
                        try:
                            result['prediction_date'] = pred_risk.Prediction_date.strftime('%B %d, %Y')
                        except Exception:
                            result['prediction_date'] = str(pred_risk.Prediction_date)
                    if "high" in pred_risk.Risk_level.lower():
                        result['doctor_advisory'] = "You have to see a doctor immediately."

                if recommendations:
                    result.update({
                        'diet': recommendations.Diet_plan,
                        'exercise': recommendations.Exercise_plan,
                        'water': recommendations.Water_intake,
                        'sleep': recommendations.Sleep_intake,
                        'weight_mgmt': recommendations.weight_management
                    })
        except Exception as e:
            print("Error retrieving view prediction page data:", e)

    if not result:
        result = {
            'risk_level': 'No Prediction Yet',
            'risk_score': 0,
            'probability': 0.0,
            'prediction': 0,
            'diet': 'Please complete a prediction assessment to view personalized recommendations.',
            'exercise': 'Please complete a prediction assessment.',
            'water': '2.5 Liters per day',
            'sleep': '7-8 Hours per day',
            'weight_mgmt': 'Maintain healthy diet and activity.'
        }

    return render(request, 'user/view_prediction.html', {'result': result})


def prediction_history(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return redirect('user_login')

    user_data = get_user_data(request)

    selected_date = request.GET.get('selected_date', '').strip() or request.POST.get('selected_date', '').strip()
    target_date = None
    selected_date_display = ""
    if selected_date:
        try:
            from datetime import datetime
            target_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
            selected_date_display = target_date.strftime('%B %d, %Y')
        except ValueError:
            target_date = None

    prediction_logs = []

    if user_data or request.user.is_authenticated:
        from django.db.models import Q
        user_filter = Q(Record_ID__User_ID__LOGIN=request.user)
        if user_data:
            user_filter |= Q(Record_ID__User_ID=user_data)

        # Query all Risk Prediction Checkups for this specific user chronologically
        all_user_preds = list(Prediction_Details.objects.filter(
            user_filter
        ).select_related('Record_ID').distinct().order_by('id'))

        user_assessment_map = {p.id: idx for idx, p in enumerate(all_user_preds, 1)}

        pred_records = list(reversed(all_user_preds))

        linked_health_rec_ids = set()

        for p_detail in pred_records:
            linked_health_rec_ids.add(p_detail.Record_ID_id)
            p_risk = Prediction_Risk.objects.filter(Prediction_ID=p_detail).last()
            
            # Ensure Prediction_Risk exists for each prediction detail
            if not p_risk:
                h_rec = p_detail.Record_ID
                h_m = h_rec.Height / 100.0 if (h_rec and h_rec.Height > 0) else 1.7
                bmi_calc = round(h_rec.Weight / (h_m * h_m), 1) if (h_rec and h_rec.Weight > 0) else 25.0
                user_age = 30
                if user_data and user_data.DOB:
                    try:
                        from datetime import date
                        today = date.today()
                        dob_val = user_data.DOB
                        if hasattr(dob_val, 'year'):
                            user_age = today.year - dob_val.year - ((today.month, today.day) < (dob_val.month, dob_val.day))
                    except Exception:
                        user_age = 30

                from .train import predict_single_sample
                res = predict_single_sample({
                    'Pregnancies': p_detail.Pregnancies,
                    'Glucose': p_detail.Glucose,
                    'BloodPressure': p_detail.Blood_Pressure,
                    'SkinThickness': p_detail.Skin_Thickness,
                    'Insulin': p_detail.Insulin,
                    'BMI': bmi_calc,
                    'DiabetesPedigreeFunction': p_detail.Diabetes_pedigree,
                    'Age': user_age
                })
                from datetime import date
                p_risk = Prediction_Risk.objects.create(
                    Prediction_ID=p_detail,
                    Risk_level=res['risk_level'],
                    Prediction_date=date.today()
                )
                Reccomendation_table.objects.create(
                    Risk_ID=p_risk,
                    Diet_plan="Balanced diet low in refined sugars.",
                    Exercise_plan="30 mins daily physical activity.",
                    Water_intake="2.5 L/day",
                    Sleep_intake="8 Hours/day",
                    weight_management="Maintain healthy weight."
                )

            if target_date and p_risk and p_risk.Prediction_date:
                p_d = p_risk.Prediction_date
                if hasattr(p_d, 'date') and not isinstance(p_d, datetime):
                    pass
                elif hasattr(p_d, 'year'):
                    pass
                if hasattr(p_d, 'strftime'):
                    if p_d.strftime('%Y-%m-%d') != selected_date:
                        continue

            rec = Reccomendation_table.objects.filter(Risk_ID=p_risk).first() if p_risk else None

            h_rec = p_detail.Record_ID
            h_m = h_rec.Height / 100.0 if (h_rec and h_rec.Height > 0) else 1.7
            bmi = round(h_rec.Weight / (h_m * h_m), 1) if (h_rec and h_rec.Weight > 0) else 25.0

            risk_lvl = p_risk.Risk_level if p_risk else 'Unknown'
            is_high_risk = 'high' in risk_lvl.lower() if risk_lvl else False

            p_date_formatted = "N/A"
            if p_risk and p_risk.Prediction_date:
                try:
                    p_date_formatted = p_risk.Prediction_date.strftime('%B %d, %Y')
                except Exception:
                    p_date_formatted = str(p_risk.Prediction_date)

            user_seq_num = user_assessment_map.get(p_detail.id, 1)

            log_entry = {
                'id': p_detail.id,
                'assessment_num': user_seq_num,
                'checkup_type': 'risk_prediction',
                'title': f'Risk Prediction Assessment #{user_seq_num}',
                'date': p_date_formatted,
                'raw_date': str(p_risk.Prediction_date) if p_risk and p_risk.Prediction_date else "",
                'risk_level': risk_lvl,
                'is_high_risk': is_high_risk,
                'glucose': p_detail.Glucose,
                'blood_pressure': p_detail.Blood_Pressure,
                'insulin': p_detail.Insulin,
                'bmi': bmi,
                'pregnancies': p_detail.Pregnancies,
                'pedigree': p_detail.Diabetes_pedigree,
                'skin_thickness': p_detail.Skin_Thickness,
                'diet': rec.Diet_plan if rec else 'Balanced diet low in refined sugars.',
                'exercise': rec.Exercise_plan if rec else '30 mins daily activity.',
                'water': rec.Water_intake if rec else '2.5 L/day',
                'sleep': rec.Sleep_intake if rec else '8 Hours/day',
                'weight_mgmt': rec.weight_management if rec else 'Maintain healthy weight.',
                'doctor_advisory': 'You have to see a doctor immediately.' if is_high_risk else None
            }
            prediction_logs.append(log_entry)

    total_predictions = len(prediction_logs)
    high_risk_count = sum(1 for p in prediction_logs if p.get('is_high_risk', False))

    return render(request, 'user/prediction_history.html', {
        'prediction_logs': prediction_logs,
        'total_predictions': total_predictions,
        'high_risk_count': high_risk_count,
        'user_data': user_data,
        'selected_date': selected_date,
        'selected_date_display': selected_date_display,
        'has_date_filter': bool(selected_date and target_date),
    })


def analytics_dashboard(request):
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return redirect('user_login')

    user_data = get_user_data(request)

    labels = []
    glucose_data = []
    bp_data = []
    insulin_data = []
    bmi_data = []
    risk_counts = {'Low Risk': 0, 'Moderate Risk': 0, 'High Risk': 0}
    logs = []

    if user_data or request.user.is_authenticated:
        from django.db.models import Q
        user_filter = Q(Record_ID__User_ID__LOGIN=request.user)
        if user_data:
            user_filter |= Q(Record_ID__User_ID=user_data)

        # Query all records chronologically (oldest to newest) for line charts
        pred_records = list(Prediction_Details.objects.filter(
            user_filter
        ).select_related('Record_ID').distinct().order_by('id'))

        user_assessment_map = {p.id: idx for idx, p in enumerate(pred_records, 1)}

        for idx, p_detail in enumerate(pred_records, 1):
            p_risk = Prediction_Risk.objects.filter(Prediction_ID=p_detail).last()
            h_rec = p_detail.Record_ID
            height_val = h_rec.Height if (h_rec and h_rec.Height is not None) else 0
            weight_val = h_rec.Weight if (h_rec and h_rec.Weight is not None) else 0

            h_m = (height_val / 100.0) if height_val > 0 else 1.7
            bmi_calc = round(weight_val / (h_m * h_m), 1) if weight_val > 0 else 25.0

            user_seq_num = user_assessment_map.get(p_detail.id, idx)
            p_date_formatted = f"Assessment #{user_seq_num}"
            if p_risk and p_risk.Prediction_date:
                try:
                    p_date_formatted = p_risk.Prediction_date.strftime('%b %d, %Y')
                except Exception:
                    p_date_formatted = str(p_risk.Prediction_date)

            risk_lvl = p_risk.Risk_level if (p_risk and p_risk.Risk_level) else 'Low Risk'
            if 'high' in risk_lvl.lower():
                r_cat = 'High Risk'
            elif 'mod' in risk_lvl.lower():
                r_cat = 'Moderate Risk'
            else:
                r_cat = 'Low Risk'

            risk_counts[r_cat] = risk_counts.get(r_cat, 0) + 1

            g_val = p_detail.Glucose if p_detail.Glucose is not None else 0
            bp_val = p_detail.Blood_Pressure if p_detail.Blood_Pressure is not None else 0
            ins_val = p_detail.Insulin if p_detail.Insulin is not None else 0

            labels.append(p_date_formatted)
            glucose_data.append(g_val)
            bp_data.append(bp_val)
            insulin_data.append(ins_val)
            bmi_data.append(bmi_calc)

            logs.append({
                'id': p_detail.id,
                'assessment_num': user_seq_num,
                'date': p_date_formatted,
                'glucose': g_val,
                'bp': bp_val,
                'insulin': ins_val,
                'bmi': bmi_calc,
                'risk_level': risk_lvl,
                'risk_cat': r_cat
            })

    import json
    context = {
        'labels_json': json.dumps(labels),
        'glucose_json': json.dumps(glucose_data),
        'bp_json': json.dumps(bp_data),
        'insulin_json': json.dumps(insulin_data),
        'bmi_json': json.dumps(bmi_data),
        'risk_counts_json': json.dumps([risk_counts['Low Risk'], risk_counts['Moderate Risk'], risk_counts['High Risk']]),
        'logs': list(reversed(logs)),
        'latest_glucose': glucose_data[-1] if glucose_data else "N/A",
        'avg_glucose': round(sum(glucose_data) / len(glucose_data), 1) if glucose_data else 0,
        'latest_bp': bp_data[-1] if bp_data else "N/A",
        'latest_bmi': bmi_data[-1] if bmi_data else "N/A",
        'total_checkups': len(logs),
        'high_risk_total': risk_counts['High Risk'],
        'user_data': user_data
    }

    return render(request, 'user/analytics_dashboard.html', context)


def recommendation_engine(request):
    user_data = get_user_data(request)

    latest_pred = None
    latest_risk = None
    latest_rec = None
    latest_health = None

    if user_data or (hasattr(request, 'user') and request.user.is_authenticated):
        from django.db.models import Q
        q_filter = Q(Record_ID__User_ID__LOGIN=request.user)
        if user_data:
            q_filter |= Q(Record_ID__User_ID=user_data)
            latest_health = Health_record.objects.filter(User_ID=user_data).last()

        latest_pred = Prediction_Details.objects.filter(q_filter).select_related('Record_ID').order_by('-id').first()
        if latest_pred:
            latest_risk = Prediction_Risk.objects.filter(Prediction_ID=latest_pred).last()
            if latest_risk:
                latest_rec = Reccomendation_table.objects.filter(Risk_ID=latest_risk).first()

    # Extract values or fallbacks
    glucose = latest_pred.Glucose if latest_pred else 100.0
    systolic_bp = 115.0
    diastolic_bp = latest_pred.Blood_Pressure if latest_pred else 75.0
    skin = latest_pred.Skin_Thickness if latest_pred else 20.0
    insulin = latest_pred.Insulin if latest_pred else 80.0
    pedigree = latest_pred.Diabetes_pedigree if latest_pred else 0.47
    pregnancies = latest_pred.Pregnancies if latest_pred else 0

    # Calculate BMI
    bmi_val = 22.0
    if latest_health and latest_health.Height > 0 and latest_health.Weight > 0:
        h_m = latest_health.Height / 100.0
        bmi_val = round(latest_health.Weight / (h_m * h_m), 1)

    risk_level = latest_risk.Risk_level if latest_risk else "Low Risk"

    # Generate Rule-Based Dietary Tips
    dietary_tips = []
    if glucose >= 200:
        dietary_tips = [
            {"title": "Strict Glycemic Control", "desc": "Eliminate refined sugars, fruit juices, and white flour completely. Focus on high-fiber non-starchy vegetables."},
            {"title": "Carbohydrate Restriction", "desc": "Limit total daily net carbohydrates to under 50-70g per day split across 3 structured meals."},
            {"title": "Low GI Protein Options", "desc": "Incorporate lean proteins such as grilled fish, skinless chicken, tofu, and egg whites to stabilize insulin spikes."},
            {"title": "Hydration with Meals", "desc": "Drink 1 glass of room-temperature water with lemon or apple cider vinegar 15 mins before mealtime."}
        ]
    elif glucose >= 126:
        dietary_tips = [
            {"title": "Controlled Carbohydrate Intake", "desc": "Replace white rice and refined bread with quinoa, oats, brown rice, and legumes."},
            {"title": "Fiber Rich Diet Goal", "desc": "Aim for 30-35 grams of dietary fiber daily (chia seeds, flaxseeds, broccoli, spinach, and avocado)."},
            {"title": "Eliminate Sugary Beverages", "desc": "Avoid soda, sweetened teas, and processed fruit juices; opt for green tea or herbal infusions."},
            {"title": "Portion Control Strategy", "desc": "Use the 50-25-25 plate rule: 50% vegetables, 25% lean protein, and 25% whole complex grains."}
        ]
    elif glucose >= 100:
        dietary_tips = [
            {"title": "Prediabetes Diet Management", "desc": "Prioritize complex carbohydrates with low glycemic index (<55 GI rating)."},
            {"title": "Balanced Snacks", "desc": "Pair carbs with protein or healthy fats (e.g., apple slices with almond butter or a handful of walnuts)."},
            {"title": "Mindful Sugar Intake", "desc": "Restrict added sugars to under 15 grams per day."},
            {"title": "Consistent Meal Schedule", "desc": "Eat at regular intervals every 4-5 hours to prevent erratic blood sugar fluctuations."}
        ]
    else:
        dietary_tips = [
            {"title": "Optimal Glycemic Maintenance", "desc": "Continue eating a vibrant Mediterranean or WHO-aligned whole-food diet."},
            {"title": "Antioxidant Rich Foods", "desc": "Include blueberries, dark leafy greens, turmeric, and berries for cellular protection."},
            {"title": "Healthy Fats Focus", "desc": "Consume extra virgin olive oil, nuts, and omega-3 rich fatty fish twice weekly."},
            {"title": "Hydration Goal", "desc": "Maintain 2.5 to 3.0 Liters of water daily to support kidney filtration."}
        ]

    # Generate Physical Activity Tips
    activity_tips = []
    if bmi_val >= 30 or "high" in risk_level.lower():
        activity_tips = [
            {"title": "Daily Structured Exercise", "desc": "45 minutes of daily brisk walking, stationary cycling, or low-impact water aerobics."},
            {"title": "Post-Meal Walking Protocol", "desc": "Take a 10-15 minute gentle walk within 30 minutes after lunch and dinner to lower postprandial glucose."},
            {"title": "Resistance & Strength Training", "desc": "Light resistance band exercises 3 times a week to improve muscle insulin sensitivity."},
            {"title": "Activity Monitoring", "desc": "Aim for at least 8,000 steps daily using a fitness tracker."}
        ]
    elif bmi_val >= 25 or "mod" in risk_level.lower():
        activity_tips = [
            {"title": "Moderate Active Goal", "desc": "150-180 minutes of moderate aerobic physical activity spread over 5 days a week."},
            {"title": "Bodyweight Strength Training", "desc": "2-3 sessions per week of squats, lunges, and core exercises to enhance glucose uptake."},
            {"title": "Reduce Sedentary Time", "desc": "Stand up and stretch for 3-5 minutes for every 45 minutes of desk or seated work."},
            {"title": "Step Goal", "desc": "Target 9,000 to 10,000 steps daily."}
        ]
    else:
        activity_tips = [
            {"title": "Aerobic Conditioning", "desc": "Maintain 150 minutes of brisk walking, swimming, cycling, or jogging weekly."},
            {"title": "Flexibility & Mobility", "desc": "Include 15-20 minutes of daily yoga or stretching routines."},
            {"title": "High-Energy Movement", "desc": "Incorporate active outdoor recreation or sports twice weekly."},
            {"title": "Target Steps", "desc": "Maintain 10,000+ daily steps for active cardiac and metabolic health."}
        ]

    # Generate Lifestyle & Habit Tips
    lifestyle_tips = []
    smoking_status = latest_health.Smoking if latest_health else "Non-Smoker"
    alcohol_status = latest_health.Alcohol if latest_health else "None"
    sleep_val = latest_health.Sleep_Duration if (latest_health and latest_health.Sleep_Duration > 0) else 7.5
    water_val = latest_health.Water_Intake if (latest_health and latest_health.Water_Intake > 0) else 2.5

    lifestyle_tips.append({"title": "Sleep Hygiene Target", "desc": f"Aim for 7.5 - 8.0 hours of uninterrupted restorative sleep nightly. (Current: {sleep_val} hrs/day)"})
    lifestyle_tips.append({"title": "Hydration Objective", "desc": f"Consume at least {water_val if water_val >= 2.5 else 2.5} Liters of clean water daily to reduce blood hyperviscosity."})

    if "smoker" in smoking_status.lower() and not "non" in smoking_status.lower():
        lifestyle_tips.append({"title": "Smoking Cessation Priority", "desc": "Smoking increases insulin resistance by 30-50% and heightens vascular risk. Consult a specialist for cessation assistance."})
    else:
        lifestyle_tips.append({"title": "Smoke-Free Environment", "desc": "Maintain smoke-free surroundings to protect microvascular arterial integrity."})

    if alcohol_status.lower() in ['frequent', 'occasional']:
        lifestyle_tips.append({"title": "Alcohol Limitation", "desc": "Alcohol can cause unpredictable hypoglycemia or liver strain. Limit to max 1 unit occasionally with meals."})
    else:
        lifestyle_tips.append({"title": "Zero Alcohol Advantage", "desc": "Abstaining from alcohol supports optimal liver gluconeogenesis and steady metabolic health."})

    # Generate Preventive Care & Screening Tips
    preventive_tips = []
    if "high" in risk_level.lower() or glucose >= 140:
        preventive_tips = [
            {"title": "HbA1c Blood Test Schedule", "desc": "Get a HbA1c test every 3 months to monitor 90-day average blood glucose levels."},
            {"title": "Comprehensive Eye Exam", "desc": "Schedule an annual dilated eye examination to screen for diabetic retinopathy."},
            {"title": "Kidney Function & Microalbumin Test", "desc": "Annual urine microalbumin and serum creatinine test to monitor renal health."},
            {"title": "Daily Foot Inspection", "desc": "Inspect feet daily for cuts, blisters, or numbness. Never walk barefoot outdoors."}
        ]
    elif "mod" in risk_level.lower() or glucose >= 100:
        preventive_tips = [
            {"title": "Bi-Annual HbA1c Screening", "desc": "Schedule HbA1c blood screening twice a year (every 6 months)."},
            {"title": "Lipid Profile & BP Check", "desc": "Check blood pressure monthly and complete a full fasting lipid panel annually."},
            {"title": "Annual Medical Checkup", "desc": "Consult your primary physician annually for comprehensive metabolic profiling."},
            {"title": "Self-Monitoring Logbook", "desc": "Maintain a log of fasting glucose and post-meal readings at least once weekly."}
        ]
    else:
        preventive_tips = [
            {"title": "Annual Wellness Screening", "desc": "Complete an annual routine wellness checkup including fasting blood sugar."},
            {"title": "Blood Pressure Monitoring", "desc": "Check blood pressure every 3-6 months (optimal target: <120/80 mmHg)."},
            {"title": "Lipid Profile Inspection", "desc": "Complete a routine lipid profile every 1-2 years."},
            {"title": "Preventive Education", "desc": "Stay updated on healthy lifestyle habits and preventive health guidelines."}
        ]

    # Calculate Wellness Prevention Score (0 to 100)
    score_val = 88
    if "high" in risk_level.lower() or glucose >= 200:
        score_val = 55
    elif "mod" in risk_level.lower() or glucose >= 126:
        score_val = 72

    context = {
        'user_data': user_data,
        'latest_pred': latest_pred,
        'latest_risk': latest_risk,
        'latest_rec': latest_rec,
        'latest_health': latest_health,
        'glucose': glucose,
        'systolic_bp': int(systolic_bp),
        'diastolic_bp': int(diastolic_bp),
        'bmi_val': bmi_val,
        'risk_level': risk_level,
        'dietary_tips': dietary_tips,
        'activity_tips': activity_tips,
        'lifestyle_tips': lifestyle_tips,
        'preventive_tips': preventive_tips,
        'wellness_score': score_val,
    }
    return render(request, 'user/recommendations.html', context)











