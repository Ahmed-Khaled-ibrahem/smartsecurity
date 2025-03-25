import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:smartsecurity/controller/appCubit/app_cubit.dart';
import 'package:smartsecurity/services/get_it.dart';
import '../../services/firebase_auth.dart';
import '../home/home.dart';
import '../login/login.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {

  @override
  Widget build(BuildContext context) {
    return StreamBuilder(
      stream: getIt<FirebaseAuthRepo>().user, builder: (context, snapshot) {
      if (snapshot.hasData) {
        return const Home();
      }
      return const LoginScreen();
    },);
  }
}
