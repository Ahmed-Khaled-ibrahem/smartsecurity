import 'package:flutter/material.dart';
import 'package:smartsecurity/services/get_it.dart';
import '../../services/firebase_auth.dart';
import '../../services/firebase_real_time.dart';

class RegisterScreen extends StatefulWidget {
  @override
  _RegisterScreenState createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _fullNameController = TextEditingController();
  final _zoneNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool isAdmin = false;
  final _adminPasswordController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Register')),
      body: GestureDetector(
        onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          transitionBuilder: (child, animation) =>
              ScaleTransition(scale: animation, child: child),
          switchInCurve: Curves.fastOutSlowIn,
          switchOutCurve: Curves.fastOutSlowIn,
          child: Builder(builder: (context) {
            if (isAdmin) {
              return Padding(
                key: const Key('key2'),
                padding: const EdgeInsets.all(16.0),
                child: Form(
                  key: _formKey,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        TextFormField(
                          controller: _fullNameController,
                          decoration:
                              const InputDecoration(labelText: 'Full Name'),
                          validator: (value) =>
                              value!.isEmpty ? 'Enter your full name' : null,
                        ),
                        TextFormField(
                          controller: _emailController,
                          decoration: const InputDecoration(labelText: 'Email'),
                          validator: (email) => emailValidator(email),
                        ),
                        TextFormField(
                          controller: _passwordController,
                          decoration:
                              const InputDecoration(labelText: 'Password'),
                          obscureText: true,
                          validator: (pass) => passwordValidator(pass),
                        ),
                        TextFormField(
                          controller: _confirmPasswordController,
                          decoration: const InputDecoration(
                              labelText: 'Confirm Password'),
                          obscureText: true,
                          validator: (value) {
                            if (value!.isEmpty) {
                              return 'Confirm your password';
                            } else if (value != _passwordController.text) {
                              return 'Passwords do not match';
                            }
                            return null;
                          },
                        ),
                        TextFormField(
                          controller: _zoneNameController,
                          decoration:
                          const InputDecoration(labelText: 'Zone Name'),
                          validator: (value) =>
                          value!.isEmpty ? 'Enter Zone name' : null,
                        ),
                        const SizedBox(height: 20),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: () async {
                              if (_formKey.currentState!.validate()) {
                                try {
                                  await getIt<FirebaseAuthRepo>()
                                      .signUpWithEmailAndPassword(
                                    _emailController.text.trim(),
                                    _passwordController.text.trim(),
                                  );
                                } catch (error) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text(error.toString())),
                                  );
                                }
                                await getIt<FirebaseAuthRepo>()
                                    .currentUser
                                    ?.updateDisplayName(
                                        _fullNameController.text.trim());
                                await getIt<FirebaseAuthRepo>()
                                    .currentUser
                                    ?.reload();
                                Navigator.pop(context);

                                await getIt<FirebaseRealTimeDB>()
                                    .addUser(
                                  _fullNameController.text.trim(),
                                  _emailController.text.trim(),
                                  _zoneNameController.text.trim(),
                                  _passwordController.text.trim(),
                                );
                              }
                            },
                            child: const Text('Register'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              );
            }
            return Padding(
                key: const Key('key'),
                padding: const EdgeInsets.all(16.0),
                child: Form(
                    key: _formKey,
                    child: SingleChildScrollView(
                        child: Column(
                      mainAxisAlignment: MainAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Text('Please enter your admin password'),
                          ],
                        ),
                        TextFormField(
                          controller: _adminPasswordController,
                          decoration:
                              const InputDecoration(labelText: 'Password'),
                          obscureText: true,
                          validator: (pass) => passwordValidator(pass),
                        ),
                        const SizedBox(height: 20),
                        const SizedBox(height: 20),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: () async {
                              if (_adminPasswordController.text.trim() ==
                                  'saraisthebest') {
                                setState(() {
                                  isAdmin = true;
                                });
                              } else {
                                ScaffoldMessenger.of(context).showSnackBar(
                                  const SnackBar(
                                      content: Text('Wrong password')),
                                );
                              }
                            },
                            child: const Text('Verify'),
                          ),
                        ),
                      ],
                    ))));
          }),
        ),
      ),
    );
  }

  emailValidator(String? email) {
    if (email == null) {
      return 'Please enter your email';
    }
    if (email.isEmpty) {
      return 'Please enter your email';
    }
    if (!email.contains('@')) {
      return 'Please enter a valid email';
    }
    if (email.length < 5) {
      return 'Please enter a valid email';
    }
    return null;
  }

  passwordValidator(String? pass) {
    if (pass == null) {
      return 'Password is required';
    }
    if (pass.isEmpty) {
      return 'Password is required';
    }
    if (pass.length < 6) {
      return 'password must be at least 6 characters';
    }
    return null;
  }
}
