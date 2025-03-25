import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:toastification/toastification.dart';

void showToast(String title,String message) {
  toastification.show(
    // context: context, // optional if you use ToastificationWrapper
    type: ToastificationType.warning,
    style: ToastificationStyle.fillColored,
    autoCloseDuration: const Duration(seconds: 5),
    title:  Text(title),
    // you can also use RichText widget for title and description parameters
    description: RichText(text:  TextSpan(text: message)),
    alignment: Alignment.topRight,
    direction: TextDirection.ltr,
    animationDuration: const Duration(milliseconds: 300),
    animationBuilder: (context, animation, alignment, child) {
      return FadeTransition(
        opacity: animation,
        child: child,
      );
    },
    icon: const Icon(Icons.warning),
    showIcon: true, // show or hide the icon
    primaryColor: Colors.red,
    backgroundColor: Colors.white,
    foregroundColor: Colors.black,
    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
    margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
    borderRadius: BorderRadius.circular(12),
    boxShadow: const [
      BoxShadow(
        color: Color(0x07000000),
        blurRadius: 16,
        offset: Offset(0, 16),
        spreadRadius: 0,
      )
    ],
    showProgressBar: true,
    closeOnClick: false,
    closeButtonShowType: CloseButtonShowType.onHover,
    pauseOnHover: true,
    dragToClose: true,
    applyBlurEffect: true,
    // callbacks: ToastificationCallbacks(
    //   onTap: (toastItem) => print('Toast ${toastItem.id} tapped'),
    //   onCloseButtonTap: (toastItem) => print('Toast ${toastItem.id} close button tapped'),
    //   onAutoCompleteCompleted: (toastItem) => print('Toast ${toastItem.id} auto complete completed'),
    //   onDismissed: (toastItem) => print('Toast ${toastItem.id} dismissed'),
    // ),
  );
  AudioPlayer().play(AssetSource('notification.mp3'));
}