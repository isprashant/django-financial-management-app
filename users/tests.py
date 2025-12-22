from django.test import TestCase

from .forms import CustomUserCreationForm


class SignupMobileValidationTests(TestCase):
    def form_data(self, username: str, mobile: str):
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password1": "Testpass123!",
            "password2": "Testpass123!",
            "mobile_number": mobile,
        }

    def test_accepts_plain_10_digit_and_normalizes(self):
        form = CustomUserCreationForm(data=self.form_data("alice", "+919876543210"))
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.profile.mobile_number, "+919876543210")

    def test_accepts_prefixed_plus_91_with_spaces_and_hyphen(self):
        form = CustomUserCreationForm(
            data=self.form_data("bob", "+91 98765-43210")
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.profile.mobile_number, "+919876543210")

    def test_rejects_leading_zero(self):
        form = CustomUserCreationForm(data=self.form_data("charlie", "0987654321"))
        self.assertFalse(form.is_valid())
        self.assertIn("mobile_number", form.errors)

    def test_rejects_non_digits(self):
        form = CustomUserCreationForm(data=self.form_data("dana", "98abc54321"))
        self.assertFalse(form.is_valid())
        self.assertIn("mobile_number", form.errors)

    def test_rejects_duplicate_even_with_different_prefix(self):
        first = CustomUserCreationForm(data=self.form_data("erin", "9876543210"))
        self.assertTrue(first.is_valid(), first.errors)
        first.save()

        duplicate = CustomUserCreationForm(
            data=self.form_data("frank", "+919876543210")
        )
        self.assertFalse(duplicate.is_valid())
        self.assertIn("mobile_number", duplicate.errors)
